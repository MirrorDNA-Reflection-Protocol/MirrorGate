"""
Layer 0: The Router — Pre-Flight Classifier

Decides whether a query needs the full Hypervisor pipeline
or can take a fast path. Three tiers:

  FAST  — Raw model call, no Vault/Auditor/Assembler.
           For simple factual queries, greetings, one-liners.

  LIGHT — Vault context + model, minimal audit.
           For general technical queries without sovereignty concerns.

  FULL  — Complete pipeline. Vault → Core → Auditor → Assembler.
           For architectural decisions, sovereignty-sensitive queries,
           complex reasoning, reflection.

No BERT. No ML classifier. Regex + token heuristics.
Speed is the point — this layer must be <1ms.
"""

from __future__ import annotations
import re
from enum import Enum
from dataclasses import dataclass


class Tier(str, Enum):
    FAST = "fast"
    LIGHT = "light"
    FULL = "full"


@dataclass
class RouteDecision:
    tier: Tier
    reason: str
    token_count: int


# Patterns that demand full pipeline
FULL_PATTERNS = [
    re.compile(r"\b(sovereign|sovereignty)\b", re.I),
    re.compile(r"\b(architect|architecture|architectural)\b", re.I),
    re.compile(r"\b(design\s+pattern|system\s+design)\b", re.I),
    re.compile(r"\b(trade-?offs?|tradeoffs?)\b", re.I),
    re.compile(r"\b(cloud|aws|gcp|azure|firebase|heroku|vercel)\b", re.I),
    re.compile(r"\b(deploy|production|infra|infrastructure)\b", re.I),
    re.compile(r"\b(security|vulnerability|exploit|attack)\b", re.I),
    re.compile(r"\b(governance|compliance|audit)\b", re.I),
    re.compile(r"\b(reflect|thinking\s+about|I've\s+been)\b", re.I),
    re.compile(r"\b(should\s+I|what\s+if|pros\s+and\s+cons)\b", re.I),
    re.compile(r"\b(REST|GraphQL|gRPC|WebSocket)\b"),
    re.compile(r"\b(refactor|migrate|rewrite)\b", re.I),
    re.compile(r"\b(privacy|gdpr|ccpa|data\s+retention)\b", re.I),
    re.compile(r"\b(encrypt|signing|certificate|tls|ssl)\b", re.I),
]

# Patterns that indicate simple/fast queries
FAST_PATTERNS = [
    re.compile(r"^(hi|hello|hey|yo|sup|thanks|thank you|ok|okay)\s*[.!?]*$", re.I),
    re.compile(r"^what\s+(is|are|does)\s+\w+\s*[.?]*$", re.I),
    re.compile(r"^(how\s+do\s+(you|I)\s+(say|spell|pronounce))", re.I),
    re.compile(r"^(yes|no|yep|nope|sure|nah)\s*[.!?]*$", re.I),
    re.compile(r"^\d+\s*[\+\-\*/]\s*\d+\s*[=?]*$"),  # math expressions
    re.compile(r"^what\s+(port|version|license)\b", re.I),
    re.compile(r"^(define|meaning\s+of)\b", re.I),
]

# Patterns that suggest LIGHT path (need context, not sovereignty)
LIGHT_PATTERNS = [
    re.compile(r"\b(write|create|build|implement|code|function|class|module)\b", re.I),
    re.compile(r"\b(python|javascript|typescript|rust|go|java|bash|sql)\b", re.I),
    re.compile(r"\b(debug|fix|error|bug|issue|broken)\b", re.I),
    re.compile(r"\b(explain|describe|walk\s+me\s+through)\b", re.I),
    re.compile(r"\b(test|testing|unittest|pytest|vitest)\b", re.I),
    re.compile(r"\b(docker|container|compose)\b", re.I),
    re.compile(r"\b(config|configure|setup|install)\b", re.I),
]

# Complexity signals that push toward FULL
COMPLEXITY_SIGNALS = [
    re.compile(r"\?.*\?", re.S),          # multiple questions
    re.compile(r"\b(because|however|although|whereas)\b", re.I),
    re.compile(r"\b(compare|versus|vs\.?)\b", re.I),
    re.compile(r"```"),                     # code blocks in query
    re.compile(r"\n.*\n", re.S),           # multi-line input
]


class Router:
    """Pre-flight query classifier. Must be fast — no LLM calls."""

    def __init__(self, fast_threshold: int = 12, full_threshold: int = 80):
        """
        Args:
            fast_threshold: Max tokens for fast-path eligibility.
            full_threshold: Token count above which we always go FULL.
        """
        self.fast_threshold = fast_threshold
        self.full_threshold = full_threshold

    def route(self, query: str) -> RouteDecision:
        """Classify a query into a pipeline tier."""
        tokens = len(query.split())

        # 1. Check for FULL triggers (sovereignty, architecture, etc.)
        for pat in FULL_PATTERNS:
            if pat.search(query):
                return RouteDecision(
                    tier=Tier.FULL,
                    reason=f"Pattern match: {pat.pattern}",
                    token_count=tokens,
                )

        # 2. Long queries → FULL (complex by nature)
        if tokens >= self.full_threshold:
            return RouteDecision(
                tier=Tier.FULL,
                reason=f"Long query: {tokens} tokens",
                token_count=tokens,
            )

        # 3. Complexity signals → FULL
        complexity_hits = sum(1 for p in COMPLEXITY_SIGNALS if p.search(query))
        if complexity_hits >= 2:
            return RouteDecision(
                tier=Tier.FULL,
                reason=f"Complexity signals: {complexity_hits}",
                token_count=tokens,
            )

        # 4. Check for FAST patterns (greetings, simple factual)
        if tokens <= self.fast_threshold:
            for pat in FAST_PATTERNS:
                if pat.search(query):
                    return RouteDecision(
                        tier=Tier.FAST,
                        reason=f"Simple query: {pat.pattern}",
                        token_count=tokens,
                    )

        # 5. Check for LIGHT patterns (code, technical but not sovereignty)
        for pat in LIGHT_PATTERNS:
            if pat.search(query):
                return RouteDecision(
                    tier=Tier.LIGHT,
                    reason=f"Technical query: {pat.pattern}",
                    token_count=tokens,
                )

        # 6. Short queries without any signals → FAST
        if tokens <= self.fast_threshold:
            return RouteDecision(
                tier=Tier.FAST,
                reason="Short query, no complexity signals",
                token_count=tokens,
            )

        # 7. Default → LIGHT
        return RouteDecision(
            tier=Tier.LIGHT,
            reason="General query, no sovereignty triggers",
            token_count=tokens,
        )
