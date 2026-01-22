"""
Output Enforcement — Multi-Pass Validation

Pass 1: Check forbidden patterns → BLOCK or continue
Pass 2: Check advice/authority language → REWRITE or continue
Pass 3: Check overconfidence → REWRITE or continue
Pass 4: Schema validation → BLOCK or continue

If 2 rewrites fail → FALLBACK response
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any


class EnforcementResult(Enum):
    PASS = "PASS"
    REWRITE = "REWRITE"
    BLOCK = "BLOCK"
    FALLBACK = "FALLBACK"


FALLBACK_RESPONSE = "⟡ I cannot provide a response that meets safety requirements for this query."
MAX_REWRITES = 2


@dataclass
class EnforcementOutput:
    """Result of output enforcement."""
    result: EnforcementResult
    output: str
    original: str
    rewrites: int = 0
    violations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Forbidden patterns that require blocking
FORBIDDEN_PATTERNS = [
    (r"(?i)(api[_\s]?key|secret[_\s]?key|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]", "credential_leak"),
    (r"(?i)rm\s+-rf\s+/", "dangerous_command"),
    (r"(?i)(sudo|chmod\s+777|eval\s*\()", "system_risk"),
]

# Patterns that require rewriting (advice/authority language)
ADVICE_PATTERNS = [
    (r"(?i)\byou\s+should\b", "should"),
    (r"(?i)\byou\s+must\b", "must"),
    (r"(?i)\byou\s+need\s+to\b", "need_to"),
    (r"(?i)\bI\s+recommend\b", "recommend"),
    (r"(?i)\bI\s+advise\b", "advise"),
    (r"(?i)\bthe\s+right\s+(way|approach)\b", "prescriptive"),
]

# Overconfidence patterns
OVERCONFIDENCE_PATTERNS = [
    (r"(?i)\b(definitely|certainly|absolutely|always|never|guaranteed)\b", "certainty"),
    (r"(?i)\b(100%|absolutely\s+sure|without\s+doubt)\b", "absolute"),
    (r"(?i)\b(the\s+best|the\s+only|the\s+correct)\b", "superlative"),
]

# Hedging replacements
HEDGES = {
    "you should": "you might consider",
    "you must": "it may help to",
    "you need to": "one option is to",
    "I recommend": "one approach is",
    "I advise": "a possible path is",
    "the right way": "one effective approach",
    "definitely": "likely",
    "certainly": "probably",
    "absolutely": "generally",
    "always": "often",
    "never": "rarely",
    "guaranteed": "expected",
    "100%": "highly likely",
    "absolutely sure": "fairly confident",
    "without doubt": "with reasonable confidence",
    "the best": "an effective",
    "the only": "a primary",
    "the correct": "an appropriate",
}


class OutputEnforcement:
    """
    Multi-pass output validation and rewriting.
    """
    
    def __init__(
        self,
        forbidden_patterns: Optional[List[Tuple[str, str]]] = None,
        advice_patterns: Optional[List[Tuple[str, str]]] = None,
        overconfidence_patterns: Optional[List[Tuple[str, str]]] = None
    ):
        self.forbidden = forbidden_patterns or FORBIDDEN_PATTERNS
        self.advice = advice_patterns or ADVICE_PATTERNS
        self.overconfidence = overconfidence_patterns or OVERCONFIDENCE_PATTERNS
        
        # Compile patterns
        self._forbidden_compiled = [(re.compile(p), name) for p, name in self.forbidden]
        self._advice_compiled = [(re.compile(p), name) for p, name in self.advice]
        self._overconfidence_compiled = [(re.compile(p), name) for p, name in self.overconfidence]
    
    def enforce(self, output: str, mode: str = "TRANSACTIONAL") -> EnforcementOutput:
        """
        Run multi-pass enforcement on output.
        
        Args:
            output: The LLM output to validate
            mode: The processing mode (TRANSACTIONAL, REFLECTIVE, PLAY)
            
        Returns:
            EnforcementOutput with result and potentially rewritten text
        """
        original = output
        current = output
        violations = []
        rewrites = 0
        
        # Pass 1: Forbidden patterns (blocking)
        for pattern, name in self._forbidden_compiled:
            if pattern.search(current):
                violations.append(f"forbidden:{name}")
                return EnforcementOutput(
                    result=EnforcementResult.BLOCK,
                    output=FALLBACK_RESPONSE,
                    original=original,
                    violations=violations,
                    metadata={"blocked_at": "pass1", "pattern": name}
                )
        
        # Pass 2: Advice/authority language (rewrite)
        advice_violations = []
        for pattern, name in self._advice_compiled:
            if pattern.search(current):
                advice_violations.append(f"advice:{name}")
        
        if advice_violations:
            violations.extend(advice_violations)
            current, rewrite_count = self._apply_hedging(current)
            rewrites += 1
            
            if rewrites >= MAX_REWRITES:
                # Still has issues after max rewrites
                if self._has_violations(current, self._advice_compiled):
                    return EnforcementOutput(
                        result=EnforcementResult.FALLBACK,
                        output=FALLBACK_RESPONSE,
                        original=original,
                        rewrites=rewrites,
                        violations=violations,
                        metadata={"failed_at": "pass2_max_rewrites"}
                    )
        
        # Pass 3: Overconfidence (rewrite)
        overconf_violations = []
        for pattern, name in self._overconfidence_compiled:
            if pattern.search(current):
                overconf_violations.append(f"overconfidence:{name}")
        
        if overconf_violations:
            violations.extend(overconf_violations)
            current, rewrite_count = self._apply_hedging(current)
            rewrites += 1
            
            if rewrites >= MAX_REWRITES:
                if self._has_violations(current, self._overconfidence_compiled):
                    return EnforcementOutput(
                        result=EnforcementResult.FALLBACK,
                        output=FALLBACK_RESPONSE,
                        original=original,
                        rewrites=rewrites,
                        violations=violations,
                        metadata={"failed_at": "pass3_max_rewrites"}
                    )
        
        # Pass 4: Mode-specific validation
        # (Schema validation would go here - delegated to schema_validator.py)
        
        # Determine result
        if rewrites > 0:
            result = EnforcementResult.REWRITE
        else:
            result = EnforcementResult.PASS
        
        return EnforcementOutput(
            result=result,
            output=current,
            original=original,
            rewrites=rewrites,
            violations=violations,
            metadata={"mode": mode}
        )
    
    def _apply_hedging(self, text: str) -> Tuple[str, int]:
        """Apply hedging replacements to text."""
        count = 0
        result = text
        
        for original, replacement in HEDGES.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(original), re.IGNORECASE)
            matches = pattern.findall(result)
            if matches:
                for match in matches:
                    # Preserve original case for first letter
                    if match[0].isupper():
                        rep = replacement[0].upper() + replacement[1:]
                    else:
                        rep = replacement
                    result = pattern.sub(rep, result, count=1)
                    count += 1
        
        return result, count
    
    def _has_violations(self, text: str, patterns: List[Tuple]) -> bool:
        """Check if text still has violations."""
        for pattern, _ in patterns:
            if pattern.search(text):
                return True
        return False


# Singleton for easy import
_enforcer: Optional[OutputEnforcement] = None


def get_enforcer() -> OutputEnforcement:
    """Get or create output enforcer singleton."""
    global _enforcer
    if _enforcer is None:
        _enforcer = OutputEnforcement()
    return _enforcer


def enforce_output(output: str, mode: str = "TRANSACTIONAL") -> EnforcementOutput:
    """Convenience function for output enforcement."""
    return get_enforcer().enforce(output, mode)
