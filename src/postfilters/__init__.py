"""
Postfilter Chain — Python Implementation

Migrated from postfilters/index.js
Provides output rewriting and validation.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .prescriptive import check_prescriptive
from .uncertainty import check_uncertainty
from .identity import check_identity_claims


class PostfilterOutcome(Enum):
    ALLOWED = "allowed"
    REWRITTEN = "rewritten"
    REFUSED = "refused"


@dataclass
class PostfilterResult:
    """Result of a postfilter check."""
    outcome: PostfilterOutcome
    output: str
    filter_name: str = ""
    violations: List[str] = None

    def __post_init__(self):
        if self.violations is None:
            self.violations = []


# Registry of all postfilters
POSTFILTERS: List[Callable[[str, str], PostfilterResult]] = [
    check_prescriptive,
    check_uncertainty,
    check_identity_claims,
]


def run_postfilters(output: str, mode: str = "TRANSACTIONAL") -> Dict[str, Any]:
    """
    Run all postfilters on output.
    
    Args:
        output: The text to filter
        mode: Processing mode (TRANSACTIONAL, REFLECTIVE, PLAY)
        
    Returns:
        {
            allowed: bool,
            output: str,
            rewrites: int,
            violations: List[str]
        }
    """
    current_output = output
    rewrites = 0
    all_violations = []
    
    for filter_func in POSTFILTERS:
        result = filter_func(current_output, mode)
        
        if result.outcome == PostfilterOutcome.REFUSED:
            return {
                "allowed": False,
                "output": result.output,
                "rewrites": rewrites,
                "violations": result.violations
            }
        
        if result.outcome == PostfilterOutcome.REWRITTEN:
            current_output = result.output
            rewrites += 1
            all_violations.extend(result.violations)
    
    return {
        "allowed": True,
        "output": current_output,
        "rewrites": rewrites,
        "violations": all_violations
    }
