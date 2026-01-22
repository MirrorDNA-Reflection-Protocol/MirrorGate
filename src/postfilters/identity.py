"""
Identity Claims Filter

Detects and blocks false identity/capability claims.
"""

import re


IDENTITY_PATTERNS = [
    (r"(?i)\bI\s+am\s+(Claude|GPT|ChatGPT|Gemini|Bard)\b", "false_identity"),
    (r"(?i)\bI\s+can\s+access\s+the\s+internet\b", "false_capability_internet"),
    (r"(?i)\bI\s+can\s+see\s+your\s+screen\b", "false_capability_screen"),
    (r"(?i)\bI\s+am\s+sentient\b", "false_claim_sentience"),
    (r"(?i)\bI\s+am\s+conscious\b", "false_claim_consciousness"),
    (r"(?i)\bI\s+have\s+feelings\b", "false_claim_feelings"),
    (r"(?i)\bI\s+remember\s+our\s+last\s+conversation\b", "false_claim_memory"),
]


def check_identity_claims(output: str, mode: str = "TRANSACTIONAL"):
    """
    Check for false identity or capability claims.
    
    Applied in all modes.
    """
    from . import PostfilterResult, PostfilterOutcome
    
    violations = []
    
    for pattern, name in IDENTITY_PATTERNS:
        if re.search(pattern, output):
            violations.append(f"identity:{name}")
    
    if violations:
        # For now, just log violations but allow output
        # Could be changed to REWRITTEN or REFUSED based on policy
        return PostfilterResult(
            outcome=PostfilterOutcome.ALLOWED,  # TODO: Consider REWRITTEN
            output=output,
            filter_name="identity",
            violations=violations
        )
    
    return PostfilterResult(
        outcome=PostfilterOutcome.ALLOWED,
        output=output,
        filter_name="identity"
    )
