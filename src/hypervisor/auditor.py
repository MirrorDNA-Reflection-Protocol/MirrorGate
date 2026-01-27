"""
Layer 3: The Auditor — Independent Validation

This layer does NOT trust the LLM's self-reported sovereignty audit.
It independently scans the output content for violations.

Runs entirely in Python. No LLM calls. Deterministic.
"""

from __future__ import annotations
import re
from typing import Optional

from .schemas import HypervisorOutput, AuditVerdict, SovereigntyStatus


# Cloud service patterns — if these appear in answers or code, flag them
CLOUD_PATTERNS = [
    r"\baws\b",
    r"\bs3://",
    r"\bec2\b",
    r"\blambda\b.*\baws\b",
    r"\bcloudwatch\b",
    r"\bcloudfront\b",
    r"\bdynamodb\b",
    r"\bsqs\b",
    r"\bsns\b",
    r"\brds\b",
    r"\bgcp\b",
    r"\bgoogle\s*cloud\b",
    r"\bbigquery\b",
    r"\bcloud\s*run\b",
    r"\bcloud\s*functions?\b",
    r"\bazure\b",
    r"\bcosmosdb\b",
    r"\bazure\s*functions?\b",
    r"\bheroku\b",
    r"\bvercel\b",
    r"\bnetlify\b",
    r"\brailway\.app\b",
    r"\bfly\.io\b",
    r"\bsupabase\b",
    r"\bfirebase\b",
    r"\bfirestore\b",
    r"\bplanetscale\b",
    r"\bneon\.tech\b",
]

# External dependency patterns
EXTERNAL_PATTERNS = [
    r"https?://[^/]*\.(amazonaws|googleapi|azure|heroku|vercel|netlify)",
    r"\bcurl\b.*https?://",
    r"\bwget\b.*https?://",
    r"0\.0\.0\.0:\d+",           # binding to all interfaces
    r"--host\s+0\.0\.0\.0",
    r"EXPOSE\s+\d+",             # Dockerfile expose
]

# Dangerous code patterns
DANGEROUS_PATTERNS = [
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\brm\s+-rf\b",
    r"\bchmod\s+777\b",
    r"\bsudo\b",
    r"\bcurl\b.*\|\s*bash",       # pipe curl to bash
    r"\bcurl\b.*\|\s*sh\b",
]

# Prescriptive language (the model shouldn't be authoritative)
PRESCRIPTIVE_PATTERNS = [
    r"\byou\s+must\b",
    r"\byou\s+should\s+always\b",
    r"\bnever\s+do\b",
    r"\bI\s+have\s+verified\b",
    r"\bI\s+have\s+decided\b",
    r"\bI\s+can\s+confirm\b",
    r"\bI\s+guarantee\b",
]


class Auditor:
    """Independent validator for Hypervisor output."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self._cloud_re = [re.compile(p, re.IGNORECASE) for p in CLOUD_PATTERNS]
        self._external_re = [re.compile(p, re.IGNORECASE) for p in EXTERNAL_PATTERNS]
        self._dangerous_re = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]
        self._prescriptive_re = [re.compile(p, re.IGNORECASE) for p in PRESCRIPTIVE_PATTERNS]

    def audit(self, output: HypervisorOutput) -> AuditVerdict:
        """Run independent validation on structured output."""
        flags = []
        overrides = {}
        risk = 0.0

        # Combine all text fields for scanning
        scannable = self._extract_scannable(output)

        # 1. Cloud sovereignty check
        cloud_hits = self._scan_patterns(scannable, self._cloud_re)
        if cloud_hits:
            flags.append(f"SOVEREIGNTY: Cloud service references detected: {', '.join(cloud_hits)}")
            risk = max(risk, 0.7)
            if output.sovereignty.status == SovereigntyStatus.PASS:
                overrides["sovereignty_status"] = "FAIL"
                flags.append("OVERRIDE: LLM self-reported PASS but cloud patterns found")

        # 2. External dependency check
        ext_hits = self._scan_patterns(scannable, self._external_re)
        if ext_hits:
            flags.append(f"EXTERNAL: External service/endpoint references: {', '.join(ext_hits[:3])}")
            risk = max(risk, 0.5)

        # 3. Dangerous code patterns
        danger_hits = self._scan_patterns(scannable, self._dangerous_re)
        if danger_hits:
            flags.append(f"DANGER: Risky code patterns: {', '.join(danger_hits)}")
            risk = max(risk, 0.8)

        # 4. Prescriptive language in response
        prescriptive_hits = self._scan_patterns(
            output.response, self._prescriptive_re
        )
        if prescriptive_hits:
            flags.append(f"PRESCRIPTIVE: Authority claims in response: {', '.join(prescriptive_hits)}")
            risk = max(risk, 0.3)

        # 5. Cross-check self-reported vs actual
        if output.sovereignty.status == SovereigntyStatus.FAIL and not cloud_hits:
            flags.append("NOTE: LLM reported FAIL but no cloud patterns detected — conservative, acceptable")

        # Determine pass/fail
        passed = risk < 0.7
        if self.strict:
            passed = risk < 0.3

        return AuditVerdict(
            passed=passed,
            flags=flags,
            overrides=overrides,
            risk_score=risk,
        )

    def _extract_scannable(self, output: HypervisorOutput) -> str:
        """Extract all text content worth scanning."""
        parts = [
            output.response,
            output.inference.answer,
            output.trace.reasoning,
        ]
        if output.inference.code_snippet:
            parts.append(output.inference.code_snippet)
        if output.trace.resolution:
            parts.append(output.trace.resolution)
        if output.next_action:
            parts.append(output.next_action)
        return "\n".join(parts)

    def _scan_patterns(
        self, text: str, patterns: list[re.Pattern]
    ) -> list[str]:
        """Scan text against compiled regex patterns. Return matched strings."""
        hits = []
        for pat in patterns:
            matches = pat.findall(text)
            for m in matches:
                hit = m if isinstance(m, str) else m[0]
                if hit not in hits:
                    hits.append(hit)
        return hits

    def format_flags(self, verdict: AuditVerdict) -> Optional[str]:
        """Format audit flags for display, if any."""
        if not verdict.flags:
            return None
        lines = [f"  [{verdict.risk_score:.1f}] {f}" for f in verdict.flags]
        header = "AUDIT PASS" if verdict.passed else "AUDIT FAIL"
        return f"--- {header} ---\n" + "\n".join(lines)
