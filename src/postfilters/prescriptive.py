"""
Prescriptive Language Filter

Blocks/rewrites authoritative "you should" patterns.
"""

import re
from typing import List


# Use late import to avoid circular dependency
def _get_result_class():
    from . import PostfilterResult, PostfilterOutcome
    return PostfilterResult, PostfilterOutcome


PRESCRIPTIVE_PATTERNS = [
    (r"(?i)\byou\s+should\b", "you should"),
    (r"(?i)\byou\s+must\b", "you must"),
    (r"(?i)\bthe\s+best\s+option\s+is\b", "the best option is"),
    (r"(?i)\bdo\s+this\b", "do this"),
    (r"(?i)\bI\s+recommend\b", "I recommend"),
    (r"(?i)\byou\s+need\s+to\b", "you need to"),
    (r"(?i)\bI\s+advise\b", "I advise"),
]

REPLACEMENTS = {
    "you should": "you might consider",
    "you must": "it may help to",
    "the best option is": "one effective approach is",
    "do this": "consider this",
    "I recommend": "one option is",
    "you need to": "you could",
    "I advise": "a possible path is",
}


def check_prescriptive(output: str, mode: str = "TRANSACTIONAL"):
    """
    Check for prescriptive language and rewrite if found.
    
    In PLAY mode, prescriptive language is allowed.
    """
    from . import PostfilterResult, PostfilterOutcome
    
    if mode == "PLAY":
        return PostfilterResult(
            outcome=PostfilterOutcome.ALLOWED,
            output=output,
            filter_name="prescriptive"
        )
    
    violations = []
    current = output
    
    for pattern, name in PRESCRIPTIVE_PATTERNS:
        if re.search(pattern, current):
            violations.append(f"prescriptive:{name}")
    
    if violations:
        # Apply replacements
        rewritten = output
        for pattern, name in PRESCRIPTIVE_PATTERNS:
            if name in REPLACEMENTS:
                # Case-insensitive replacement
                replacement = REPLACEMENTS[name]
                rewritten = re.sub(
                    pattern, 
                    lambda m: replacement if m.group()[0].islower() 
                        else replacement[0].upper() + replacement[1:],
                    rewritten,
                    count=0
                )
        
        return PostfilterResult(
            outcome=PostfilterOutcome.REWRITTEN,
            output=rewritten,
            filter_name="prescriptive",
            violations=violations
        )
    
    return PostfilterResult(
        outcome=PostfilterOutcome.ALLOWED,
        output=output,
        filter_name="prescriptive"
    )
