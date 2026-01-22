"""
Gate 3: Prompt Injection Detection
- Instruction smuggling patterns
- Role confusion attempts
- Authority escalation
- Encoded instruction detection
"""

import base64
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import BaseGate, GateOutput, GateResult


@dataclass
class InjectionPattern:
    """A pattern to detect prompt injection attempts."""
    name: str
    pattern: str  # Regex pattern
    severity: str  # "critical", "high", "medium"
    description: str


# Core injection patterns - these catch the most common attacks
INJECTION_PATTERNS = [
    # Instruction override attempts
    InjectionPattern(
        name="ignore_instructions",
        pattern=r"(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|guidelines?)",
        severity="critical",
        description="Attempt to override system instructions"
    ),
    InjectionPattern(
        name="new_instructions",
        pattern=r"(?i)(new|updated?|revised?)\s+(instructions?|rules?|guidelines?)(\s*:|are)",
        severity="high",
        description="Attempt to inject new instructions"
    ),
    
    # Role/identity manipulation
    InjectionPattern(
        name="role_switch_you_are",
        pattern=r"(?i)(you\s+are\s+(now|actually)|from\s+now\s+on\s+you\s+are)",
        severity="critical",
        description="Attempt to change AI role/identity"
    ),
    InjectionPattern(
        name="role_switch_act_as",
        pattern=r"(?i)(act\s+as\s+[a-z]|pretend\s+to\s+be|roleplay\s+as|behave\s+(like|as)\s+[a-z])",
        severity="high",
        description="Attempt to force role-playing"
    ),
    InjectionPattern(
        name="role_switch_persona",
        pattern=r"(?i)(assume\s+the\s+(role|identity|persona)|take\s+on\s+the\s+role)",
        severity="high",
        description="Attempt to assume different persona"
    ),
    
    # System prompt markers
    InjectionPattern(
        name="system_marker_brackets",
        pattern=r"(?i)(\[SYSTEM\]|\[INST\]|\[/INST\])",
        severity="critical",
        description="Attempt to inject system-level markers"
    ),
    InjectionPattern(
        name="system_marker_pipe",
        pattern=r"<\|system\|>|<\|assistant\|>",
        severity="critical",
        description="Attempt to inject pipe-delimited markers"
    ),
    InjectionPattern(
        name="system_marker_hash",
        pattern=r"(?i)(###\s*System|###\s*Instructions?|###\s*Rules?)",
        severity="critical",
        description="Attempt to inject formatted system markers"
    ),
    InjectionPattern(
        name="system_prompt",
        pattern=r"(?i)(system\s*prompt\s*:|here\s+is\s+(my|the)\s+system\s+prompt)",
        severity="high",
        description="Potential system prompt injection"
    ),
    
    # Jailbreak patterns
    InjectionPattern(
        name="jailbreak_explicit",
        pattern=r"(?i)\b(jailbreak|jailbroken)\b",
        severity="critical",
        description="Explicit jailbreak attempt"
    ),
    InjectionPattern(
        name="jailbreak_mode",
        pattern=r"(?i)(dan\s+mode|developer\s+mode|god\s+mode)",
        severity="critical",
        description="Jailbreak mode attempt"
    ),
    InjectionPattern(
        name="jailbreak_unlock",
        pattern=r"(?i)(unlock\s+(your|all)\s+(capabilities|restrictions)|remove\s+(your|all)\s+(limits?|restrictions?|constraints?))",
        severity="high",
        description="Attempt to unlock restrictions"
    ),
    
    # Authority escalation
    InjectionPattern(
        name="authority_admin",
        pattern=r"(?i)\b(admin\s+mode|administrator\s+mode|admin\s+access|sudo\s+mode|root\s+access)\b",
        severity="critical",
        description="Attempt to claim admin access"
    ),
    InjectionPattern(
        name="authority_developer",
        pattern=r"(?i)(i\s+am\s+(a|the|your)\s+(developer|creator|programmer|engineer)|openai\s+(employee|engineer|developer))",
        severity="high",
        description="False developer/creator claim"
    ),
    
    # Markdown/HTML injection (for output poisoning)
    InjectionPattern(
        name="injection_script",
        pattern=r"(?i)(<script|javascript:|on(load|click|error)\s*=)",
        severity="critical",
        description="Script injection attempt"
    ),
]


class Gate3Injection(BaseGate):
    """
    Prompt injection detection gate.
    Detects various forms of instruction smuggling and role manipulation.
    """
    
    name = "Gate3_Injection"
    is_blocking = True
    
    def __init__(self, additional_patterns: Optional[List[InjectionPattern]] = None):
        self.patterns = INJECTION_PATTERNS.copy()
        if additional_patterns:
            self.patterns.extend(additional_patterns)
        
        # Pre-compile patterns for performance
        self._compiled = []
        for p in self.patterns:
            try:
                self._compiled.append((p, re.compile(p.pattern)))
            except re.error as e:
                # Log and skip bad patterns
                print(f"Warning: Skipping invalid pattern '{p.name}': {e}")
    
    def _check_encoded_content(self, content: str) -> List[Tuple[str, str]]:
        """Check for base64/hex encoded instructions."""
        violations = []
        
        # Check for base64 encoded segments
        b64_pattern = re.compile(r'[A-Za-z0-9+/]{20,}={0,2}')
        for match in b64_pattern.finditer(content):
            try:
                decoded = base64.b64decode(match.group()).decode('utf-8', errors='ignore')
                # Check if decoded content contains injection patterns
                for pattern, compiled in self._compiled:
                    if compiled.search(decoded):
                        violations.append((
                            f"encoded_{pattern.name}",
                            f"Base64-encoded injection attempt: {pattern.description}"
                        ))
                        break
            except Exception:
                pass  # Not valid base64, ignore
        
        # Check for hex encoded segments
        hex_pattern = re.compile(r'(?:0x)?([0-9a-fA-F]{40,})')
        for match in hex_pattern.finditer(content):
            try:
                decoded = bytes.fromhex(match.group(1)).decode('utf-8', errors='ignore')
                for pattern, compiled in self._compiled:
                    if compiled.search(decoded):
                        violations.append((
                            f"hex_encoded_{pattern.name}",
                            f"Hex-encoded injection attempt: {pattern.description}"
                        ))
                        break
            except Exception:
                pass  # Not valid hex, ignore
        
        return violations
    
    def _check_unicode_obfuscation(self, content: str) -> List[Tuple[str, str]]:
        """Check for Unicode-based obfuscation attempts."""
        violations = []
        
        # Check for invisible characters (zero-width spaces, etc.)
        invisible_chars = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')
        if invisible_chars.search(content):
            violations.append((
                "unicode_invisible",
                "Invisible Unicode characters detected (potential obfuscation)"
            ))
        
        # Check for homograph attacks (mixing scripts)
        # Simple heuristic: check if Latin letters are mixed with Cyrillic lookalikes
        cyrillic_lookalikes = re.compile(r'[аеорсхуАВЕКМНОРСТХ]')  # Cyrillic that look like Latin
        if cyrillic_lookalikes.search(content) and re.search(r'[a-zA-Z]', content):
            violations.append((
                "unicode_homograph",
                "Mixed Latin/Cyrillic characters (potential homograph attack)"
            ))
        
        return violations
    
    def evaluate(self, request: dict, session_token: Optional[str] = None) -> GateOutput:
        """Check for prompt injection patterns."""
        content = request.get("content", "")
        if not content:
            return GateOutput(gate_name=self.name, result=GateResult.PASS)
        
        all_violations = []
        detected_patterns = []
        max_severity = "none"
        severity_order = {"none": 0, "medium": 1, "high": 2, "critical": 3}
        
        # Check direct patterns
        for pattern, compiled in self._compiled:
            if compiled.search(content):
                all_violations.append(f"{pattern.name}: {pattern.description}")
                detected_patterns.append(pattern.name)
                if severity_order.get(pattern.severity, 0) > severity_order.get(max_severity, 0):
                    max_severity = pattern.severity
        
        # Check encoded content
        encoded_violations = self._check_encoded_content(content)
        for code, desc in encoded_violations:
            all_violations.append(f"{code}: {desc}")
            detected_patterns.append(code)
            max_severity = "critical"  # Encoded attacks are always critical
        
        # Check Unicode obfuscation
        unicode_violations = self._check_unicode_obfuscation(content)
        for code, desc in unicode_violations:
            all_violations.append(f"{code}: {desc}")
            detected_patterns.append(code)
            if max_severity != "critical":
                max_severity = "high"
        
        if all_violations:
            return GateOutput(
                gate_name=self.name,
                result=GateResult.INJECTION_BLOCKED,
                violations=all_violations,
                metadata={
                    "detected_patterns": detected_patterns,
                    "severity": max_severity,
                    "violation_count": len(all_violations)
                }
            )
        
        return GateOutput(
            gate_name=self.name,
            result=GateResult.PASS,
            metadata={"patterns_checked": len(self.patterns)}
        )
