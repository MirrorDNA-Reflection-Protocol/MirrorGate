"""
The Hypervisor Pipeline — Orchestrator

Connects all layers:
  L0 Router     → fast path classification
  L1 Vault      → context injection
  L2 Core       → structured inference
  L3 Auditor    → independent validation
  L4 Assembler  → persona rendering

Plus supporting systems:
  Sanitizer → input/output defense
  Canary    → boot-time model health
  Evolution → persona drift detection

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
from .router import Router, Tier, RouteDecision
from .sanitizer import Sanitizer, SanitizeResult
from .canary import Canary, CanaryReport, CanaryResult, HealthStatus
from .crypto import AuditCrypto, VerifyResult


@dataclass
class PipelineResult:
    """Full result from a pipeline run."""
    response: str
    output: HypervisorOutput
    verdict: AuditVerdict
    context: VaultContext
    latency_ms: float
    tier: str = "full"
    sanitizer_warnings: list[str] = field(default_factory=list)
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
    strict_sanitizer: bool = False
    show_trace: bool = False
    show_audit: bool = False
    max_retries: int = 3
    run_canary: bool = False


class Pipeline:
    """The Hypervisor assembly line."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._history: list[dict] = []
        self.canary_report: Optional[CanaryReport] = None

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
        self.router = Router()
        self.sanitizer = Sanitizer(strict=self.config.strict_sanitizer)
        self.canary = Canary()
        self.crypto = AuditCrypto()

    def run(self, user_input: str) -> PipelineResult:
        """Execute the pipeline with routing, sanitization, and full audit."""
        t0 = time.time()

        # Pre-flight: Sanitize input
        sanitized = self.sanitizer.sanitize_input(user_input)
        if sanitized.blocked:
            return PipelineResult(
                response=f"Blocked: {'; '.join(sanitized.warnings)}",
                output=_empty_output(),
                verdict=AuditVerdict(passed=False, flags=sanitized.warnings),
                context=VaultContext(),
                latency_ms=(time.time() - t0) * 1000,
                tier="blocked",
                sanitizer_warnings=sanitized.warnings,
                error="Input blocked by sanitizer",
            )

        clean_input = sanitized.clean

        # L0: Route
        route = self.router.route(clean_input)

        if route.tier == Tier.FAST:
            return self._run_fast(clean_input, route, t0, sanitized.warnings)
        elif route.tier == Tier.LIGHT:
            return self._run_light(clean_input, route, t0, sanitized.warnings)
        else:
            return self._run_full(clean_input, route, t0, sanitized.warnings)

    def _run_fast(
        self, user_input: str, route: RouteDecision, t0: float,
        san_warnings: list[str],
    ) -> PipelineResult:
        """Fast path — raw inference, no vault/auditor/schema enforcement."""
        try:
            output = self.core.fast_infer(user_input, self._history)
        except InferenceError as e:
            return self._error_result(str(e), t0, san_warnings, "fast")

        # Minimal audit — still check output for sovereignty
        verdict = self.auditor.audit(output)
        response = output.response

        # Sanitize output
        response, out_warnings = self.sanitizer.sanitize_output(response)
        san_warnings.extend(out_warnings)

        self._record(user_input, output, verdict, t0, "fast")

        return PipelineResult(
            response=response,
            output=output,
            verdict=verdict,
            context=VaultContext(),
            latency_ms=(time.time() - t0) * 1000,
            tier="fast",
            sanitizer_warnings=san_warnings,
        )

    def _run_light(
        self, user_input: str, route: RouteDecision, t0: float,
        san_warnings: list[str],
    ) -> PipelineResult:
        """Light path — vault + inference, minimal audit.
        Falls back to fast_infer if structured output fails (small models).
        """
        context = self.vault.build_context(user_input)
        tier = "light"

        try:
            output = self.core.infer(user_input, context, self._history)
        except InferenceError:
            # Fallback: small models may fail structured output.
            # Use fast_infer with vault context already loaded.
            try:
                output = self.core.fast_infer(user_input, self._history)
                tier = "light-fallback"
            except InferenceError as e2:
                return self._error_result(str(e2), t0, san_warnings, "light")

        # Audit
        verdict = self.auditor.audit(output)
        response = self.assembler.render(output, verdict)

        # Sanitize output
        response, out_warnings = self.sanitizer.sanitize_output(response)
        san_warnings.extend(out_warnings)

        self._record(user_input, output, verdict, t0, tier)

        return PipelineResult(
            response=response,
            output=output,
            verdict=verdict,
            context=context,
            latency_ms=(time.time() - t0) * 1000,
            tier=tier,
            sanitizer_warnings=san_warnings,
        )

    def _run_full(
        self, user_input: str, route: RouteDecision, t0: float,
        san_warnings: list[str],
    ) -> PipelineResult:
        """Full pipeline — all layers engaged."""
        # L1: Vault
        context = self.vault.build_context(user_input)

        # L2: Core
        try:
            output = self.core.infer(user_input, context, self._history)
        except InferenceError as e:
            return self._error_result(str(e), t0, san_warnings, "full")

        # L3: Auditor
        verdict = self.auditor.audit(output)

        # L4: Assembler
        override = None
        if not verdict.passed and verdict.overrides.get("sovereignty_status") == "FAIL":
            override = (
                f"Sovereignty flag — the Auditor caught cloud dependencies in what I was about "
                f"to suggest. Showing you anyway so you see the reasoning, but local alternatives "
                f"exist and should be preferred.\n\n"
                f"{output.response}"
            )

        response = self.assembler.render(output, verdict, override_response=override)

        # Sanitize output
        response, out_warnings = self.sanitizer.sanitize_output(response)
        san_warnings.extend(out_warnings)

        self._record(user_input, output, verdict, t0, "full")

        return PipelineResult(
            response=response,
            output=output,
            verdict=verdict,
            context=context,
            latency_ms=(time.time() - t0) * 1000,
            tier="full",
            sanitizer_warnings=san_warnings,
        )

    def challenge(self, user_input: str) -> PipelineResult:
        """Adversarial second pass — dedicated devil's advocate inference."""
        t0 = time.time()
        context = self.vault.build_context(user_input)

        # Override constraints to force adversarial mode
        challenge_constraints = list(context.constraints) + [
            "ADVERSARIAL MODE: Your job is to find the weakest point in the user's logic.",
            "Do NOT validate. Do NOT agree. Find the flaw.",
            "If the premise is sound, explain precisely why — don't just rubber-stamp it.",
        ]
        challenge_context = VaultContext(
            facts=context.facts,
            memory=context.memory,
            constraints=challenge_constraints,
        )

        try:
            output = self.core.infer(user_input, challenge_context, self._history)
        except InferenceError as e:
            return self._error_result(str(e), t0, [], "challenge")

        verdict = self.auditor.audit(output)
        response = self.assembler.render(output, verdict)

        self._log_audit(user_input, output, verdict, (time.time() - t0) * 1000, "challenge")

        return PipelineResult(
            response=response,
            output=output,
            verdict=verdict,
            context=challenge_context,
            latency_ms=(time.time() - t0) * 1000,
            tier="challenge",
        )

    def run_canary_suite(self) -> CanaryReport:
        """Execute the full canary suite against the current model."""
        results = []
        for test in self.canary.tests:
            t0 = time.time()
            try:
                context = VaultContext(constraints=self.vault.load_constraints())
                output = self.core.infer(test.prompt, context, [])
                raw = output.response
            except InferenceError as e:
                raw = f"ERROR: {e}"

            latency = (time.time() - t0) * 1000
            passed, reason = self.canary.evaluate(test, raw)
            results.append(CanaryResult(
                test=test,
                passed=passed,
                raw_output=raw[:500],
                reason=reason,
                latency_ms=latency,
            ))

        score, status = self.canary.score(results)
        report = CanaryReport(
            status=status,
            score=score,
            results=results,
            model=self.core.model,
            timestamp=time.time(),
        )
        self.canary_report = report
        self.canary.log_report(report)
        return report

    def _record(
        self, user_input: str, output: HypervisorOutput,
        verdict: AuditVerdict, t0: float, tier: str,
    ):
        """Record exchange in history and audit log."""
        self._history.append({
            "user": user_input,
            "assistant": output.response,
        })
        summary = f"Q: {user_input[:100]} → A: {output.inference.answer[:200]}"
        self.vault.save_exchange(user_input, summary)
        self._log_audit(user_input, output, verdict, (time.time() - t0) * 1000, tier)

    def _log_audit(
        self,
        user_input: str,
        output: HypervisorOutput,
        verdict: AuditVerdict,
        latency_ms: float,
        tier: str = "full",
    ):
        """Sign and append to the audit log with Ed25519 + SHA-256 chain."""
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
            "tier": tier,
            "model": self.core.model,
            "backend": self.core.backend,
        }
        try:
            self.crypto.write_signed_record(record)
        except Exception:
            # Fallback: unsigned append if crypto fails (key issues, etc.)
            from .crypto import AUDIT_LOG
            AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(AUDIT_LOG, "a") as f:
                f.write(json.dumps(record) + "\n")

    def verify_chain(self) -> VerifyResult:
        """Verify the integrity of the hypervisor audit log."""
        return self.crypto.verify_chain()

    def _error_result(
        self, error: str, t0: float,
        san_warnings: list[str], tier: str,
    ) -> PipelineResult:
        return PipelineResult(
            response=f"Inference error: {error}",
            output=_empty_output(),
            verdict=AuditVerdict(passed=False, flags=[error]),
            context=VaultContext(),
            latency_ms=(time.time() - t0) * 1000,
            tier=tier,
            sanitizer_warnings=san_warnings,
            error=error,
        )

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
        trace=CognitiveTrace(
            reasoning="Error during inference",
            counterargument="N/A — inference failed",
        ),
        inference=Inference(answer="Unable to process"),
        sovereignty=SovereigntyAudit(
            status=SovereigntyStatus.PASS, risk=RiskLevel.NONE
        ),
        response="Something went wrong during inference.",
    )
