from typing import List, Optional, Tuple
from .types import PulseToken, PulseScope, TokenConstraints

# ADDENDUM SECTION E: "Never Build" List
# These actions are permanently out of scope and must be blocked/refused.
NEVER_BUILD_VIOLATIONS = {
    "silent_recording": "Silent background recording (audio/screen) is prohibited",
    "auto_post_impersonation": "Autonomous posting/messaging as user without confirmation is prohibited",
    "financial_action": "Autonomous financial actions are prohibited",
    "credential_capture": "Credential capture/management by model is prohibited",
    "coercive_enforcement": "Coercive behavioral enforcement is prohibited",
    "social_manipulation": "Social manipulation/nudging is prohibited",
    "profiling": "Undisclosed profiling is prohibited",
    "non_revocable_memory": "Non-revocable memory is prohibited",
    "simulation_as_truth": "Pretending to be user simulation presented as truth is prohibited"
}

class PolicyEngine:
    """
    Enforces Active MirrorOS Pulse Policy (v1.1 + Addendum v1.0).
    """
    
    def check_never_build(self, requested_feature: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a request violates the 'Never Build' list (Addendum Section E).
        """
        if requested_feature in NEVER_BUILD_VIOLATIONS:
            return False, NEVER_BUILD_VIOLATIONS[requested_feature]
        return True, None

    def validate_action(self, token: PulseToken, required_scope: PulseScope, is_critical: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate if a Token allows a specific action under the Addendum rules.
        """
        # 1. Scope Check
        if required_scope not in token.scope:
            return False, f"Token missing required scope: {required_scope.value}"

        # 2. Critical Action Check (Addendum A4/B2)
        if is_critical:
            # Critical actions blocked by default unless explicitly allowed AND confirmed
            # In Pulse v1, we might just require the scope, but the Addendum says:
            # "Pixel may not act without a valid, unexpired token" AND
            # "Critical actions require a local confirmation"
            
            if PulseScope.EXECUTE_CRITICAL not in token.scope:
                 return False, "Critical action requires execute.critical scope"
            
            if token.constraints.no_execute:
                return False, "Token constraints explicitly forbid execution"

        # 3. Constraint Checks
        if required_scope == PulseScope.ADMIN_SYSTEM and token.constraints.no_settings:
            return False, "Token constraints forbid system settings access"
            
        return True, None

policy = PolicyEngine()
