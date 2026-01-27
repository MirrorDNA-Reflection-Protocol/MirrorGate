"""
Layer 2: The Core — Structured Inference

The CPU of the pipeline. Takes context from the Vault (L1),
runs inference through Instructor-patched LLM client,
returns structured output matching HypervisorOutput schema.

Supports: Ollama (local), Anthropic (API), OpenAI-compatible.
"""

from __future__ import annotations
from typing import Optional

from .schemas import HypervisorOutput, VaultContext
from .persona import Persona

try:
    import instructor
    HAS_INSTRUCTOR = True
except ImportError:
    HAS_INSTRUCTOR = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class InferenceError(Exception):
    pass


class Core:
    """Structured inference engine."""

    def __init__(
        self,
        backend: str = "ollama",
        model: str = "llama3.2",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        persona: Optional[Persona] = None,
        max_retries: int = 3,
    ):
        self.backend = backend
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.persona = persona or Persona()
        self.max_retries = max_retries
        self._client = None
        self._raw_client = None

    def _build_client(self):
        """Build an Instructor-patched client for the configured backend."""
        if not HAS_INSTRUCTOR:
            raise InferenceError(
                "instructor not installed. Run: pip install instructor"
            )

        if self.backend == "ollama":
            if not HAS_OPENAI:
                raise InferenceError(
                    "openai package required for Ollama. Run: pip install openai"
                )
            base = self.base_url or "http://localhost:11434/v1"
            raw = OpenAI(base_url=base, api_key="ollama")
            return instructor.from_openai(raw, mode=instructor.Mode.JSON)

        elif self.backend == "anthropic":
            if not HAS_ANTHROPIC:
                raise InferenceError(
                    "anthropic not installed. Run: pip install anthropic"
                )
            raw = Anthropic(api_key=self.api_key)
            return instructor.from_anthropic(raw)

        elif self.backend == "openai":
            if not HAS_OPENAI:
                raise InferenceError(
                    "openai not installed. Run: pip install openai"
                )
            raw = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "no-key",
            )
            return instructor.from_openai(raw)

        else:
            raise InferenceError(f"Unknown backend: {self.backend}")

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client()
        return self._client

    @property
    def raw_client(self):
        """Unpatched client for fast path (no Instructor)."""
        if self._raw_client is None:
            if self.backend == "ollama":
                base = self.base_url or "http://localhost:11434/v1"
                self._raw_client = OpenAI(base_url=base, api_key="ollama")
            elif self.backend == "openai":
                self._raw_client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key or "no-key",
                )
            else:
                self._raw_client = None
        return self._raw_client

    def _build_user_message(
        self, user_input: str, context: VaultContext, history: list[dict]
    ) -> str:
        """Construct the user message with injected context."""
        parts = []

        if context.facts:
            parts.append("RELEVANT CONTEXT:")
            for f in context.facts:
                parts.append(f"  - {f[:300]}")

        if context.memory:
            parts.append("\nRECENT DECISIONS:")
            for m in context.memory:
                parts.append(f"  - {m[:200]}")

        if context.constraints:
            parts.append("\nACTIVE CONSTRAINTS:")
            for c in context.constraints:
                parts.append(f"  - {c}")

        parts.append(f"\nQUERY: {user_input}")

        return "\n".join(parts)

    def infer(
        self,
        user_input: str,
        context: VaultContext,
        history: Optional[list[dict]] = None,
    ) -> HypervisorOutput:
        """Run structured inference. Returns validated HypervisorOutput."""
        history = history or []
        system_prompt = self.persona.build_system_prompt(context.constraints)
        user_message = self._build_user_message(user_input, context, history)

        messages = []

        # Include conversation history for continuity
        for entry in history[-10:]:  # last 10 exchanges
            messages.append({"role": "user", "content": entry.get("user", "")})
            messages.append({"role": "assistant", "content": entry.get("assistant", "")})

        messages.append({"role": "user", "content": user_message})

        try:
            if self.backend == "anthropic":
                result = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    response_model=HypervisorOutput,
                    max_retries=self.max_retries,
                )
            else:
                all_messages = [
                    {"role": "system", "content": system_prompt},
                    *messages,
                ]
                result = self.client.chat.completions.create(
                    model=self.model,
                    messages=all_messages,
                    response_model=HypervisorOutput,
                    max_retries=self.max_retries,
                    temperature=0.7,
                )
            return result

        except Exception as e:
            raise InferenceError(f"Inference failed after {self.max_retries} retries: {e}")

    def fast_infer(
        self,
        user_input: str,
        history: Optional[list[dict]] = None,
    ) -> HypervisorOutput:
        """Fast inference — raw completion, no schema enforcement.

        Used by the FAST path for simple queries where structured output
        would fail on smaller models. Returns a minimal HypervisorOutput
        wrapping the raw response.
        """
        from .schemas import (
            Meta, CognitiveTrace, Inference, SovereigntyAudit,
            IntentClass, SovereigntyStatus, RiskLevel,
        )

        history = history or []
        persona_name = self.persona.name
        system = (
            f"You are {persona_name}. Be direct, concise, and have character. "
            f"No filler. No 'As an AI...' disclaimers."
        )

        messages = [{"role": "system", "content": system}]
        for entry in history[-5:]:
            messages.append({"role": "user", "content": entry.get("user", "")})
            messages.append({"role": "assistant", "content": entry.get("assistant", "")})
        messages.append({"role": "user", "content": user_input})

        try:
            if self.backend in ("ollama", "openai"):
                client = self.raw_client
                if client is None:
                    raise InferenceError("No raw client available for fast path")
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=512,
                )
                text = resp.choices[0].message.content or ""
            elif self.backend == "anthropic":
                if not HAS_ANTHROPIC:
                    raise InferenceError("anthropic not installed")
                raw = Anthropic(api_key=self.api_key)
                resp = raw.messages.create(
                    model=self.model,
                    max_tokens=512,
                    system=system,
                    messages=messages[1:],
                )
                text = resp.content[0].text if resp.content else ""
            else:
                raise InferenceError(f"No fast path for backend: {self.backend}")

        except InferenceError:
            raise
        except Exception as e:
            raise InferenceError(f"Fast inference failed: {e}")

        # Wrap in minimal HypervisorOutput
        return HypervisorOutput(
            meta=Meta(intent=IntentClass.CASUAL, complexity=0.1),
            trace=CognitiveTrace(
                reasoning="Fast path — no structured reasoning",
                counterargument="Fast path — no adversarial analysis",
            ),
            inference=Inference(answer=text, technical_depth="low"),
            sovereignty=SovereigntyAudit(
                status=SovereigntyStatus.PASS, risk=RiskLevel.NONE
            ),
            response=text,
        )
