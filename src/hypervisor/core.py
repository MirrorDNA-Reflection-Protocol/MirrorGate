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
