"""
The Hypervisor Pipeline — Orchestrator

Connects all four layers:
  L1 Vault    → context injection
  L2 Core     → structured inference
  L3 Auditor  → independent validation
  L4 Assembler → persona rendering

This is the single entry point for a query.
"""

from __future__ import annotations
import time
import json
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from .schemas import HypervisorOutput, AuditVerdict, VaultContext
from .vault import Vault
from .core import Core, InferenceError
from .auditor import Auditor
from .assembler import Assembler
from .persona import Persona


AUDIT_LOG = Path.home() / ".mirrorgate" / "logs" / "hypervisor.jsonl"


@dataclass
class PipelineResult:
    """Full result from a pipeline run."""
    response: str
    output: HypervisorOutput
    verdict: AuditVerdict
    context: VaultContext
    latency_ms: float
    error: Optional[str] = None


@dataclass
class PipelineConfig:
    """Configuration for the Hypervisor pipeline."""
    backend: str = "ollama"
    model: str = "llama3.2"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    persona_path: Optional[str] = None
    vault_dir: Optional[str] = None
    strict_audit: bool = False
    show_trace: bool = False
    show_audit: bool = False
    max_retries: int = 3


class Pipeline:
    """The Hypervisor assembly line."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._history: list[dict] = []

        # Initialize layers
        self.persona = Persona(config_path=self.config.persona_path)
        self.vault = Vault(persist_dir=self.config.vault_dir)
        self.core = Core(
            backend=self.config.backend,
            model=self.config.model,
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            persona=self.persona,
            max_retries=self.config.max_retries,
        )
        self.auditor = Auditor(strict=self.config.strict_audit)
        self.assembler = Assembler(
            show_trace=self.config.show_trace,
            show_audit=self.config.show_audit,
        )

    def run(self, user_input: str) -> PipelineResult:
        """Execute the full pipeline for a user query."""
        t0 = time.time()

        # L1: Vault — fetch context
        context = self.vault.build_context(user_input)

        # L2: Core — structured inference
        try:
            output = self.core.infer(user_input, context, self._history)
        except InferenceError as e:
            return PipelineResult(
                response=f"Inference error: {e}",
                output=_empty_output(),
                verdict=AuditVerdict(passed=False, flags=[str(e)]),
                context=context,
                latency_ms=(time.time() - t0) * 1000,
                error=str(e),
            )

        # L3: Auditor — independent validation
        verdict = self.auditor.audit(output)

        # L4: Assembler — render final response
        override = None
        if not verdict.passed and verdict.overrides.get("sovereignty_status") == "FAIL":
            # Don't replace the response — show it with context.
            # The sovereignty alert header from the Assembler already flags the issue.
            # But prepend a note from the persona acknowledging the catch.
            override = (
                f"Sovereignty flag — the Auditor caught cloud dependencies in what I was about "
                f"to suggest. Showing you anyway so you see the reasoning, but local alternatives "
                f"exist and should be preferred.\n\n"
                f"{output.response}"
            )

        response = self.assembler.render(output, verdict, override_response=override)

        # Record in history
        self._history.append({
            "user": user_input,
            "assistant": output.response,
        })

        # Save to vault memory
        summary = f"Q: {user_input[:100]} → A: {output.inference.answer[:200]}"
        self.vault.save_exchange(user_input, summary)

        # Append to audit log
        latency = (time.time() - t0) * 1000
        self._log_audit(user_input, output, verdict, latency)

        return PipelineResult(
            response=response,
            output=output,
            verdict=verdict,
            context=context,
            latency_ms=latency,
        )

    def _log_audit(
        self,
        user_input: str,
        output: HypervisorOutput,
        verdict: AuditVerdict,
        latency_ms: float,
    ):
        """Append to the audit log."""
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": int(time.time()),
            "query_hash": hashlib.sha256(user_input.encode()).hexdigest()[:16],
            "intent": output.meta.intent.value,
            "complexity": output.meta.complexity,
            "sovereignty_self": output.sovereignty.status.value,
            "audit_passed": verdict.passed,
            "audit_risk": verdict.risk_score,
            "audit_flags": len(verdict.flags),
            "latency_ms": round(latency_ms, 1),
        }
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")

    @property
    def history(self) -> list[dict]:
        return self._history

    def clear_history(self):
        self._history.clear()


def _empty_output() -> HypervisorOutput:
    """Fallback empty output for error cases."""
    from .schemas import (
        Meta, CognitiveTrace, Inference, SovereigntyAudit,
        IntentClass, SovereigntyStatus, RiskLevel,
    )
    return HypervisorOutput(
        meta=Meta(intent=IntentClass.CASUAL, complexity=0.0),
        trace=CognitiveTrace(reasoning="Error during inference"),
        inference=Inference(answer="Unable to process"),
        sovereignty=SovereigntyAudit(
            status=SovereigntyStatus.PASS, risk=RiskLevel.NONE
        ),
        response="Something went wrong during inference.",
    )
