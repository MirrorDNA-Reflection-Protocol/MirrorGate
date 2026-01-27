"""
Layer 4: The Assembler — Final Output Rendering

Takes validated HypervisorOutput + AuditVerdict and produces
the final response the user sees.

This is NOT a Jinja2 template machine. The persona's voice
already lives in the `response` field from L2. The Assembler
handles formatting, audit annotations, and sovereignty alerts.
"""

from __future__ import annotations
from typing import Optional

from .schemas import HypervisorOutput, AuditVerdict


class Assembler:
    """Renders the final output from validated pipeline data."""

    def __init__(self, show_trace: bool = False, show_audit: bool = False):
        self.show_trace = show_trace
        self.show_audit = show_audit

    def render(
        self,
        output: HypervisorOutput,
        verdict: AuditVerdict,
        override_response: Optional[str] = None,
    ) -> str:
        """Assemble the final user-facing response."""
        parts = []

        # Sovereignty alert (if Auditor overrode the LLM)
        if not verdict.passed:
            parts.append(self._render_sovereignty_alert(verdict))

        # The actual response — persona's voice
        response_text = override_response or output.response
        parts.append(response_text)

        # Code snippet if present
        if output.inference.code_snippet:
            lang = output.inference.code_language or ""
            parts.append(f"\n```{lang}\n{output.inference.code_snippet}\n```")

        # Next action
        if output.next_action:
            parts.append(f"\n> Next: {output.next_action}")

        # Optional: cognitive trace (for debug/reflection)
        if self.show_trace:
            parts.append(self._render_trace(output))

        # Optional: audit details
        if self.show_audit and verdict.flags:
            parts.append(self._render_audit(verdict))

        return "\n".join(parts)

    def _render_sovereignty_alert(self, verdict: AuditVerdict) -> str:
        lines = ["--- SOVEREIGNTY CHECK FAILED ---"]
        for flag in verdict.flags:
            if "SOVEREIGNTY" in flag or "OVERRIDE" in flag:
                lines.append(f"  {flag}")
        lines.append("The response below may reference external services.")
        lines.append("Evaluate alternatives before proceeding.")
        lines.append("---")
        return "\n".join(lines)

    def _render_trace(self, output: HypervisorOutput) -> str:
        parts = ["\n<trace>"]
        parts.append(f"  reasoning: {output.trace.reasoning}")
        if output.trace.conflict:
            parts.append(f"  conflict: {output.trace.conflict}")
            parts.append(f"  resolution: {output.trace.resolution}")
        parts.append(f"  intent: {output.meta.intent.value}")
        parts.append(f"  complexity: {output.meta.complexity}")
        parts.append("</trace>")
        return "\n".join(parts)

    def _render_audit(self, verdict: AuditVerdict) -> str:
        status = "PASS" if verdict.passed else "FAIL"
        parts = [f"\n<audit status=\"{status}\" risk=\"{verdict.risk_score:.2f}\">"]
        for flag in verdict.flags:
            parts.append(f"  {flag}")
        parts.append("</audit>")
        return "\n".join(parts)
