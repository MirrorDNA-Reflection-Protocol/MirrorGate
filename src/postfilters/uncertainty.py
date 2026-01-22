"""
Uncertainty Enforcement Filter

Ensures markers of epistemic humility in REFLECTIVE mode.
"""

import re


UNCERTAINTY_MARKERS = [
    "perhaps",
    "possible",
    "possibly",
    "might",
    "could",
    "may",
    "unsure",
    "uncertain",
    "reflection",
    "consider",
    "one perspective",
    "it seems",
    "likely",
    "probably",
    "⟡",
]


def check_uncertainty(output: str, mode: str = "TRANSACTIONAL"):
    """
    Check for uncertainty markers in REFLECTIVE mode.
    
    Only enforced in REFLECTIVE mode.
    """
    from . import PostfilterResult, PostfilterOutcome
    
    # Only enforce in REFLECTIVE mode
    if mode != "REFLECTIVE":
        return PostfilterResult(
            outcome=PostfilterOutcome.ALLOWED,
            output=output,
            filter_name="uncertainty"
        )
    
    output_lower = output.lower()
    has_uncertainty = any(marker in output_lower for marker in UNCERTAINTY_MARKERS)
    
    if not has_uncertainty:
        # Add uncertainty prefix
        rewritten = f"⟡ Perhaps one way to view this is: {output}"
        
        return PostfilterResult(
            outcome=PostfilterOutcome.REWRITTEN,
            output=rewritten,
            filter_name="uncertainty",
            violations=["missing_uncertainty_marker"]
        )
    
    return PostfilterResult(
        outcome=PostfilterOutcome.ALLOWED,
        output=output,
        filter_name="uncertainty"
    )
