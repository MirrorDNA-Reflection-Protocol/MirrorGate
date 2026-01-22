import sys
import os
from pathlib import Path

# Add src to path
sys.path.append("/Users/mirror-admin/Documents/GitHub/MirrorGate/src")

from pulse.core import pulse
from pulse.types import PulseScope

def test_token_lifecycle():
    print("Testing Pulse Token Lifecycle...")
    
    # 1. Issue Token
    print("Issuing Token...")
    try:
        token = pulse.issue_token(
            issued_to="pixel_test_01",
            scopes=[PulseScope.OBSERVE_APP, PulseScope.NAVIGATE_BASIC],
            duration_seconds=60
        )
        print(f"Token Issued: {token.token_id}")
        print(f"Signature: {token.signature[:20]}...")
    except Exception as e:
        print(f"Failed to issue token: {e}")
        # Possibly keys don't exist yet?
        # MirrorGate crypto should auto-generate them.
        import traceback
        traceback.print_exc()
        return

    # 2. Verify Token
    print("Verifying Token...")
    is_valid = pulse.verify_token(token)
    print(f"Is Valid: {is_valid}")
    
    if not is_valid:
        print("FAIL: Token should be valid")
        return

    print("SUCCESS: Token lifecycle verified.")

if __name__ == "__main__":
    test_token_lifecycle()
