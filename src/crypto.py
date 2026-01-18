#!/usr/bin/env python3
"""
MirrorGate Cryptographic Layer

- Ed25519 key generation and signing
- UUID-v7 event IDs
- SHA-256 hash chaining
- Tamper-evident decision records
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    import uuid6 as uuid_mod
    def uuid7() -> str:
        return str(uuid_mod.uuid7())
except ImportError:
    import uuid
    def uuid7() -> str:
        # Fallback to uuid4 if uuid6/uuid7 not available
        return str(uuid.uuid4())

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64

MIRRORGATE_DIR = Path.home() / ".mirrorgate"
KEYS_DIR = MIRRORGATE_DIR / "keys"
AUDIT_LOG = MIRRORGATE_DIR / "audit_log.jsonl"
CHAIN_STATE = MIRRORGATE_DIR / "chain_state.json"

MIRRORGATE_VERSION = "2.0"


def ensure_directories():
    """Create MirrorGate directories if they don't exist."""
    MIRRORGATE_DIR.mkdir(exist_ok=True)
    KEYS_DIR.mkdir(exist_ok=True)


def generate_keypair() -> tuple:
    """Generate Ed25519 keypair and save to disk."""
    ensure_directories()
    
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Save private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    (KEYS_DIR / "private.pem").write_bytes(private_pem)
    
    # Save public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    (KEYS_DIR / "public.pem").write_bytes(public_pem)
    
    return private_key, public_key


def load_private_key() -> Ed25519PrivateKey:
    """Load private key from disk, generate if not exists."""
    private_path = KEYS_DIR / "private.pem"
    
    if not private_path.exists():
        private_key, _ = generate_keypair()
        return private_key
    
    private_pem = private_path.read_bytes()
    return serialization.load_pem_private_key(private_pem, password=None)


def get_previous_hash() -> str:
    """Get the hash of the previous record for chaining."""
    if not CHAIN_STATE.exists():
        return "GENESIS"
    
    try:
        state = json.loads(CHAIN_STATE.read_text())
        return state.get("last_hash", "GENESIS")
    except:
        return "GENESIS"


def save_chain_state(last_hash: str):
    """Save the latest hash for chain continuity."""
    ensure_directories()
    CHAIN_STATE.write_text(json.dumps({
        "last_hash": last_hash,
        "updated": datetime.now(timezone.utc).isoformat()
    }))


def compute_file_hash(path: str) -> str:
    """Compute SHA-256 hash of file contents."""
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return "FILE_NOT_FOUND"
    except Exception as e:
        return f"ERROR:{str(e)[:20]}"


# Policy files for hash computation
POLICY_FILES = [
    Path(__file__).parent / "rules.py",
    Path(__file__).parent.parent / "config" / "rules.yaml",
    Path(__file__).parent.parent / "config" / "output_schemas.yaml",
    Path(__file__).parent.parent / "config" / "tripwires.yaml",
]


def compute_policy_hash() -> str:
    """
    Compute hash of current policy state.
    
    Combines hashes of:
    - rules.py content
    - config/rules.yaml
    - config/output_schemas.yaml
    - config/tripwires.yaml
    
    This enables "which policy was active" verification.
    """
    combined = hashlib.sha256()
    
    for policy_file in POLICY_FILES:
        if policy_file.exists():
            try:
                content = policy_file.read_bytes()
                combined.update(content)
            except Exception:
                combined.update(b"UNREADABLE:" + str(policy_file).encode())
        else:
            combined.update(b"MISSING:" + str(policy_file).encode())
    
    return combined.hexdigest()[:16]  # Truncate for readability


def get_rules_version() -> str:
    """Get version of rules configuration."""
    rules_file = Path(__file__).parent.parent / "config" / "rules.yaml"
    if rules_file.exists():
        try:
            import yaml
            with open(rules_file, 'r') as f:
                data = yaml.safe_load(f)
                return data.get("version", "1.0")
        except Exception:
            pass
    return "1.0"


def generate_decision_record(
    action: str,
    resource: str,
    violation_code: Optional[str],
    hash_before: str,
    hash_after: str,
    actor: str = "agent"
) -> Dict[str, Any]:
    """
    Generate a cryptographically signed decision record.
    
    Args:
        action: "ALLOW" or "BLOCK"
        resource: Path to the resource
        violation_code: Code if blocked, None if allowed
        hash_before: SHA-256 of file before write
        hash_after: SHA-256 of file after write
        actor: Who initiated the action
        
    Returns:
        Complete signed decision record
    """
    ensure_directories()
    
    # Get previous hash for chaining
    prev_hash = get_previous_hash()
    
    # Build record
    record = {
        "event_id": uuid7(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "resource": resource,
        "violation_code": violation_code,
        "hash_before": hash_before,
        "hash_after": hash_after,
        "policy_hash": compute_policy_hash(),
        "rules_version": get_rules_version(),
        "mirror_gate_version": MIRRORGATE_VERSION
    }
    
    # Compute chain hash
    record_bytes = json.dumps(record, sort_keys=True).encode()
    chain_input = record_bytes + prev_hash.encode()
    chain_hash = hashlib.sha256(chain_input).hexdigest()
    record["chain_hash"] = chain_hash
    
    # Sign the record
    private_key = load_private_key()
    signature = private_key.sign(chain_hash.encode())
    record["signature"] = base64.b64encode(signature).decode()
    
    # Save chain state
    save_chain_state(chain_hash)
    
    return record


def append_to_audit_log(record: Dict[str, Any]):
    """Append a decision record to the audit log."""
    ensure_directories()
    
    with open(AUDIT_LOG, 'a') as f:
        f.write(json.dumps(record) + '\n')


def verify_chain() -> tuple:
    """
    Verify the integrity of the audit log chain.
    
    Returns:
        Tuple of (is_valid: bool, error_message: str|None)
    """
    if not AUDIT_LOG.exists():
        return True, None
    
    prev_hash = "GENESIS"
    
    with open(AUDIT_LOG, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
            except json.JSONDecodeError:
                return False, f"Invalid JSON at line {line_num}"
            
            # Reconstruct the chain hash
            stored_chain_hash = record.pop("chain_hash", None)
            stored_signature = record.pop("signature", None)
            
            record_bytes = json.dumps(record, sort_keys=True).encode()
            chain_input = record_bytes + prev_hash.encode()
            computed_hash = hashlib.sha256(chain_input).hexdigest()
            
            if computed_hash != stored_chain_hash:
                return False, f"Chain broken at line {line_num}: hash mismatch"
            
            prev_hash = stored_chain_hash
    
    return True, None
