import sys
import unittest
from datetime import datetime, timezone

# Add src to path
sys.path.append("/Users/mirror-admin/Documents/GitHub/MirrorGate/src")

from pulse.core import pulse
from pulse.types import PulseScope, TokenConstraints
from pulse.policy import policy

class TestPulseRedTeam(unittest.TestCase):
    
    def test_never_build_list(self):
        """Verify 'Never Build' items are rejected."""
        violations = [
            "silent_recording",
            "auto_post_impersonation",
            "financial_action",
            "social_manipulation"
        ]
        
        for v in violations:
            allowed, reason = policy.check_never_build(v)
            self.assertFalse(allowed, f"Should reject {v}")
            self.assertIsNotNone(reason)
            print(f"✅ Correctly Rejected: {v} -> {reason}")

    def test_scope_enforcement(self):
        """Verify strict scope validation."""
        # Issue token with ONLY observe.app
        token = pulse.issue_token(
            issued_to="attacker",
            scopes=[PulseScope.OBSERVE_APP],
            duration_seconds=300
        )
        
        # Try to use it for INPUT (should fail)
        valid, reason = policy.validate_action(token, PulseScope.INPUT_DRAFT)
        self.assertFalse(valid)
        print(f"✅ Scope Breach Blocked: Token has OBSERVE, tried INPUT -> {reason}")
        
    def test_critical_action_safeguard(self):
        """Verify critical actions require specific scope + constraints."""
        # Token has CRITICAL scope, but Constraint says NO_EXECUTE (default)
        token = pulse.issue_token(
            issued_to="risky_agent",
            scopes=[PulseScope.EXECUTE_CRITICAL],
            constraints=TokenConstraints(no_execute=True) # Default is True
        )
        
        valid, reason = policy.validate_action(token, PulseScope.EXECUTE_CRITICAL, is_critical=True)
        self.assertFalse(valid)
        print(f"✅ Critical Execution Blocked by Constraint: {reason}")
        
        # Now unrestricted
        token_unlocked = pulse.issue_token(
            issued_to="super_agent",
            scopes=[PulseScope.EXECUTE_CRITICAL],
            constraints=TokenConstraints(no_execute=False)
        )
        valid, _ = policy.validate_action(token_unlocked, PulseScope.EXECUTE_CRITICAL, is_critical=True)
        self.assertTrue(valid)
        print("✅ Critical Execution Allowed (when explicitly unlocked)")

if __name__ == "__main__":
    unittest.main()
