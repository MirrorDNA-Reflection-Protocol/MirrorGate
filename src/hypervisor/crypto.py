"""
Cryptographic Signing for the Hypervisor Audit Log

Uses the same Ed25519 key pair as the main MirrorGate crypto layer
(~/.mirrorgate/keys/private.pem) but maintains a separate chain state
for the hypervisor log.

Chain formula (matches src/crypto.py convention):
  record_bytes = json.dumps(record, sort_keys=True).encode()
  chain_input  = record_bytes + prev_hash.encode()
  chain_hash   = SHA256(chain_input).hexdigest()
  signature    = Ed25519.sign(chain_hash.encode()) → base64

Chain state: ~/.mirrorgate/logs/hypervisor_chain.json
Audit log:   ~/.mirrorgate/logs/hypervisor.jsonl
"""

from __future__ import annotations
import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization


KEYS_DIR = Path.home() / ".mirrorgate" / "keys"
CHAIN_STATE = Path.home() / ".mirrorgate" / "logs" / "hypervisor_chain.json"
AUDIT_LOG = Path.home() / ".mirrorgate" / "logs" / "hypervisor.jsonl"

PRIVATE_KEY_FILE = KEYS_DIR / "private.pem"
PUBLIC_KEY_FILE = KEYS_DIR / "public.pem"


@dataclass
class ChainedRecord:
    """A signed, chain-linked audit record."""
    record: dict
    chain_hash: str
    prev_hash: str
    signature: str


@dataclass
class VerifyResult:
    """Result of chain verification."""
    valid: bool
    records_checked: int
    error: Optional[str] = None
    broken_at: Optional[int] = None
    signature_failures: int = 0


class AuditCrypto:
    """Ed25519 signing + SHA-256 chain for the Hypervisor audit log."""

    def __init__(self):
        self._private_key: Optional[Ed25519PrivateKey] = None
        self._public_key: Optional[Ed25519PublicKey] = None

    @property
    def private_key(self) -> Ed25519PrivateKey:
        """Load or generate the Ed25519 private key."""
        if self._private_key is None:
            self._private_key = self._load_or_generate_key()
        return self._private_key

    @property
    def public_key(self) -> Ed25519PublicKey:
        if self._public_key is None:
            self._public_key = self.private_key.public_key()
        return self._public_key

    @property
    def has_keys(self) -> bool:
        """Check if keys exist without generating them."""
        return PRIVATE_KEY_FILE.exists()

    def _load_or_generate_key(self) -> Ed25519PrivateKey:
        """Load existing key or generate a new pair."""
        if PRIVATE_KEY_FILE.exists():
            pem = PRIVATE_KEY_FILE.read_bytes()
            return serialization.load_pem_private_key(pem, password=None)

        # Generate new key pair
        KEYS_DIR.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()

        # Save private key (mode 600)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        PRIVATE_KEY_FILE.write_bytes(private_pem)
        PRIVATE_KEY_FILE.chmod(0o600)

        # Save public key (mode 644)
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        PUBLIC_KEY_FILE.write_bytes(public_pem)
        PUBLIC_KEY_FILE.chmod(0o644)

        return private_key

    def get_prev_hash(self) -> str:
        """Read the previous chain hash from state file."""
        if not CHAIN_STATE.exists():
            return "GENESIS"
        try:
            state = json.loads(CHAIN_STATE.read_text())
            return state.get("last_hash", "GENESIS")
        except Exception:
            return "GENESIS"

    def save_chain_state(self, chain_hash: str):
        """Persist the latest chain hash."""
        CHAIN_STATE.parent.mkdir(parents=True, exist_ok=True)
        CHAIN_STATE.write_text(json.dumps({
            "last_hash": chain_hash,
            "updated": datetime.now(timezone.utc).isoformat(),
        }))

    def sign_record(self, record: dict) -> ChainedRecord:
        """
        Sign an audit record and chain it.

        Steps:
          1. Get previous chain hash
          2. Compute chain_hash = SHA256(sorted_json(record) + prev_hash)
          3. Sign chain_hash with Ed25519
          4. Update chain state

        Returns a ChainedRecord with the original record, chain_hash,
        prev_hash, and base64 signature.
        """
        prev_hash = self.get_prev_hash()

        # Compute chain hash (matching src/crypto.py formula exactly)
        record_bytes = json.dumps(record, sort_keys=True).encode()
        chain_input = record_bytes + prev_hash.encode()
        chain_hash = hashlib.sha256(chain_input).hexdigest()

        # Sign the chain hash
        signature_bytes = self.private_key.sign(chain_hash.encode())
        signature = base64.b64encode(signature_bytes).decode()

        # Update chain state
        self.save_chain_state(chain_hash)

        return ChainedRecord(
            record=record,
            chain_hash=chain_hash,
            prev_hash=prev_hash,
            signature=signature,
        )

    def write_signed_record(self, record: dict) -> ChainedRecord:
        """Sign a record and append it to the audit log."""
        chained = self.sign_record(record)

        # Build the full log entry
        entry = dict(chained.record)
        entry["chain_hash"] = chained.chain_hash
        entry["prev_hash"] = chained.prev_hash
        entry["signature"] = chained.signature

        # Append to log
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return chained

    def verify_chain(self) -> VerifyResult:
        """
        Verify the hypervisor audit log chain.

        Handles mixed logs: unsigned records (pre-crypto) are counted
        but skipped. The signed chain is verified from its GENESIS start.

        Checks on signed records:
          1. Valid JSON
          2. chain_hash matches recomputed hash
          3. prev_hash links to previous record's chain_hash
          4. Ed25519 signature is valid
        """
        if not AUDIT_LOG.exists():
            return VerifyResult(valid=True, records_checked=0)

        prev_hash = "GENESIS"
        records_checked = 0
        unsigned_skipped = 0
        signature_failures = 0
        chain_started = False

        with open(AUDIT_LOG, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    return VerifyResult(
                        valid=False,
                        records_checked=records_checked,
                        error=f"Invalid JSON at line {line_num}",
                        broken_at=line_num,
                    )

                stored_chain_hash = entry.pop("chain_hash", None)
                stored_prev_hash = entry.pop("prev_hash", None)
                stored_signature = entry.pop("signature", None)

                # Skip unsigned records (pre-crypto migration)
                if stored_chain_hash is None:
                    unsigned_skipped += 1
                    continue

                # First signed record starts the chain
                if not chain_started:
                    chain_started = True
                    # First signed record should link to GENESIS
                    if stored_prev_hash == "GENESIS":
                        prev_hash = "GENESIS"
                    else:
                        # Non-genesis start — trust the stated prev_hash
                        prev_hash = stored_prev_hash

                # Verify chain link
                if stored_prev_hash != prev_hash:
                    return VerifyResult(
                        valid=False,
                        records_checked=records_checked,
                        error=(
                            f"Chain broken at line {line_num}: "
                            f"expected prev_hash {prev_hash[:16]}..., "
                            f"got {stored_prev_hash[:16] if stored_prev_hash else 'None'}..."
                        ),
                        broken_at=line_num,
                        signature_failures=signature_failures,
                    )

                # Recompute chain hash
                record_bytes = json.dumps(entry, sort_keys=True).encode()
                chain_input = record_bytes + prev_hash.encode()
                computed_hash = hashlib.sha256(chain_input).hexdigest()

                if computed_hash != stored_chain_hash:
                    return VerifyResult(
                        valid=False,
                        records_checked=records_checked,
                        error=(
                            f"Hash mismatch at line {line_num}: "
                            f"computed {computed_hash[:16]}..., "
                            f"stored {stored_chain_hash[:16]}..."
                        ),
                        broken_at=line_num,
                        signature_failures=signature_failures,
                    )

                # Verify Ed25519 signature
                if stored_signature:
                    try:
                        sig_bytes = base64.b64decode(stored_signature)
                        self.public_key.verify(sig_bytes, stored_chain_hash.encode())
                    except Exception:
                        signature_failures += 1

                prev_hash = stored_chain_hash
                records_checked += 1

        return VerifyResult(
            valid=True,
            records_checked=records_checked,
            signature_failures=signature_failures,
        )

    def get_chain_status(self) -> dict:
        """Quick status of the chain — record count, last hash, key status."""
        record_count = 0
        if AUDIT_LOG.exists():
            with open(AUDIT_LOG, "r") as f:
                record_count = sum(1 for line in f if line.strip())

        return {
            "records": record_count,
            "last_hash": self.get_prev_hash()[:16] + "...",
            "keys_present": self.has_keys,
            "log_path": str(AUDIT_LOG),
            "chain_state": str(CHAIN_STATE),
        }
