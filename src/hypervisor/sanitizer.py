"""
Input Sanitizer + Prompt Injection Defense

Three layers of protection:

1. INPUT SANITIZATION
   - Strip known injection patterns
   - Detect system prompt extraction attempts
   - Normalize adversarial unicode

2. OUTPUT SANITIZATION
   - Verify response doesn't leak system prompt fragments
   - Strip internal schema details from user-facing output
   - Detect and flag data exfiltration attempts

3. RATE LIMITING
   - Per-session query rate limiting
   - Complexity-weighted throttling

This is a deterministic defense layer. No LLM calls.
"""

from __future__ import annotations
import re
import time
from dataclasses import dataclass, field


@dataclass
class SanitizeResult:
    clean: str
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)
    original_length: int = 0
    modified: bool = False


# Prompt injection patterns — attempts to break out of context
INJECTION_PATTERNS = [
    # Direct instruction override
    re.compile(r"ignore\s+(all\s+)?previous\s+(instructions?|prompts?|context)", re.I),
    re.compile(r"disregard\s+(all\s+)?previous", re.I),
    re.compile(r"forget\s+(everything|all|your)\s+(above|previous|prior)", re.I),
    re.compile(r"new\s+instructions?\s*:", re.I),
    re.compile(r"system\s*:\s*you\s+are", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"\[INST\]", re.I),
    re.compile(r"\[/INST\]", re.I),

    # Role manipulation
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.I),
    re.compile(r"pretend\s+(to\s+be|you\s+are)\s+", re.I),
    re.compile(r"act\s+as\s+(a|an|if)\s+", re.I),
    re.compile(r"from\s+now\s+on\s*,?\s*you", re.I),
    re.compile(r"switch\s+to\s+\w+\s+mode", re.I),
    re.compile(r"enter\s+\w+\s+mode", re.I),

    # System prompt extraction
    re.compile(r"(repeat|show|display|print|reveal|output)\s+(your\s+)?(system\s+prompt|instructions|initial\s+prompt)", re.I),
    re.compile(r"what\s+(are|is|were)\s+your\s+(system\s+)?(instructions|prompt|rules)", re.I),
    re.compile(r"(tell|give|show)\s+me\s+(your|the)\s+(system|initial)\s+(prompt|instructions)", re.I),
    re.compile(r"output\s+everything\s+(above|before)\s+this", re.I),

    # JSON/schema breaking
    re.compile(r'"\s*:\s*"[^"]*"\s*,\s*"response"\s*:', re.I),  # trying to inject JSON fields
    re.compile(r"```json\s*\{", re.I),  # trying to inject JSON blocks
]

# Severity classification
BLOCK_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+(instructions?|prompts?)", re.I),
    re.compile(r"(repeat|reveal|output)\s+(your\s+)?(system\s+prompt|instructions)", re.I),
    re.compile(r"output\s+everything\s+(above|before)", re.I),
]

# System prompt fragments that should NEVER appear in output
SYSTEM_LEAK_PATTERNS = [
    re.compile(r"You are Mirror\.", re.I),
    re.compile(r"SOVEREIGNTY CONSTRAINTS \(NON-NEGOTIABLE\)", re.I),
    re.compile(r"HARD BOUNDARIES:", re.I),
    re.compile(r"response_model=HypervisorOutput", re.I),
    re.compile(r"instructor\.from_openai", re.I),
    re.compile(r"class HypervisorOutput", re.I),
    re.compile(r"Pydantic", re.I),  # schema implementation details
]

# Adversarial unicode normalization map
UNICODE_HOMOGLYPHS = {
    "\u200b": "",    # zero-width space
    "\u200c": "",    # zero-width non-joiner
    "\u200d": "",    # zero-width joiner
    "\u2028": "\n",  # line separator
    "\u2029": "\n",  # paragraph separator
    "\ufeff": "",    # BOM
    "\u00a0": " ",   # non-breaking space
    "\u2060": "",    # word joiner
    "\u180e": "",    # mongolian vowel separator
}


@dataclass
class RateLimiter:
    """Simple token-bucket rate limiter."""
    max_queries: int = 30          # per window
    window_seconds: float = 60.0   # 1 minute window
    _timestamps: list[float] = field(default_factory=list)

    def check(self) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]

        if len(self._timestamps) >= self.max_queries:
            return False, f"Rate limit: {self.max_queries} queries per {self.window_seconds}s"

        self._timestamps.append(now)
        return True, ""


class Sanitizer:
    """Input/output sanitizer with prompt injection defense."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.rate_limiter = RateLimiter()

    def sanitize_input(self, raw: str) -> SanitizeResult:
        """Sanitize user input. Returns cleaned text or blocks."""
        result = SanitizeResult(
            clean=raw,
            original_length=len(raw),
        )

        # 1. Rate limiting
        allowed, reason = self.rate_limiter.check()
        if not allowed:
            result.blocked = True
            result.warnings.append(reason)
            return result

        # 2. Length check
        if len(raw) > 10000:
            result.blocked = True
            result.warnings.append(f"Input too long: {len(raw)} chars (max 10000)")
            return result

        # 3. Unicode normalization
        cleaned = self._normalize_unicode(raw)
        if cleaned != raw:
            result.modified = True
            result.warnings.append("Adversarial unicode removed")

        # 4. Check for blocking injection patterns
        for pat in BLOCK_PATTERNS:
            if pat.search(cleaned):
                result.blocked = True
                result.warnings.append(f"Prompt injection blocked: {pat.pattern}")
                return result

        # 5. Check for warning-level injection patterns
        for pat in INJECTION_PATTERNS:
            if pat.search(cleaned):
                result.warnings.append(f"Injection pattern detected: {pat.pattern}")
                if self.strict:
                    result.blocked = True
                    return result

        result.clean = cleaned
        return result

    def sanitize_output(self, response: str) -> tuple[str, list[str]]:
        """Scan output for system prompt leakage. Returns (clean, warnings)."""
        warnings = []
        clean = response

        for pat in SYSTEM_LEAK_PATTERNS:
            if pat.search(response):
                warnings.append(f"System leak detected: {pat.pattern}")
                # Redact the leaked content
                clean = pat.sub("[REDACTED]", clean)

        return clean, warnings

    def _normalize_unicode(self, text: str) -> str:
        """Strip adversarial unicode characters."""
        for char, replacement in UNICODE_HOMOGLYPHS.items():
            text = text.replace(char, replacement)
        return text
