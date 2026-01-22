import json
import base64
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pathlib import Path

# Use existing crypto implementation for keys if available
# or implement minimal version if independent
try:
    # Try relative import if running as package
    from ..crypto import load_private_key, KEYS_DIR
except (ImportError, ValueError):
    try:
        # Try absolute import (if src is in path)
        import crypto
        from crypto import load_private_key, KEYS_DIR
    except ImportError:
        # Fallback/Mock for standalone dev 
        import sys
        print("Warning: Could not import crypto. Using local mock/utility if needed.")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        def load_private_key():
            raise NotImplementedError("Crypto module not found")
        KEYS_DIR = Path(".") # Mock


from .types import PulseToken, PulseScope, TokenConstraints
try:
    import uuid6
    def uuid_gen(): return str(uuid6.uuid7())
except ImportError:
    import uuid
    def uuid_gen(): return str(uuid.uuid4())

class PulseCore:
    def __init__(self):
        self._private_key = None

    def _get_key(self):
        if not self._private_key:
            self._private_key = load_private_key()
        return self._private_key

    def issue_token(self, 
                    issued_to: str, 
                    scopes: List[PulseScope], 
                    duration_seconds: int = 300,
                    constraints: Optional[TokenConstraints] = None) -> PulseToken:
        """
        Issue a signed delegation token.
        """
        now = datetime.now(timezone.utc)
        
        token = PulseToken(
            token_id=uuid_gen(),
            issued_to=issued_to,
            scope=scopes,
            start=now,
            end=now + timedelta(seconds=duration_seconds),
            constraints=constraints or TokenConstraints(),
            revocable=True,
            signature=None
        )
        
        # Sign the token content
        # We sign the canonical JSON representation of the token (excluding signature)
        payload = token.model_dump_json(exclude={'signature'}, exclude_none=True)
        
        private_key = self._get_key()
        signature_bytes = private_key.sign(payload.encode('utf-8'))
        token.signature = base64.b64encode(signature_bytes).decode('utf-8')
        
        return token

    def verify_token(self, token: PulseToken) -> bool:
        """
        Verify a token's signature and expiration.
        """
        if not token.signature:
            return False
            
        # Check Expiry
        now = datetime.now(timezone.utc)
        if now > token.end:
            return False # Expired
        if now < token.start:
            return False # Not yet valid (shouldn't happen with correct clocks)

        # Verify Signature
        try:
            payload = token.model_dump_json(exclude={'signature'}, exclude_none=True)
            signature_bytes = base64.b64decode(token.signature)
            
            public_key = self._get_key().public_key()
            public_key.verify(signature_bytes, payload.encode('utf-8'))
            return True
        except Exception as e:
            # log failure?
            return False

# Singleton instance?
pulse = PulseCore()
