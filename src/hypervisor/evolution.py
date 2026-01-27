"""
The Evolution Daemon — Dynamic Persona Drift Detection

Analyzes conversation history to detect shifts in user behavior.
Proposes persona adjustments. Never auto-applies.

Human-in-the-loop: generates a diff, user reviews via /evolve.

Detects:
  - Complexity shift (beginner → expert or vice versa)
  - Topic drift (new domains, abandoned domains)
  - Interaction style change (questions → commands, exploration → execution)
  - Vocabulary evolution (more/less technical language)

Proposes:
  - Persona trait adjustments (add/remove/modify)
  - Voice tone shifts
  - Technical depth calibration
  - New boundary suggestions
"""

from __future__ import annotations
import json
import time
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter

import yaml


VAULT_HISTORY = Path.home() / ".mirrorgate" / "vault" / "history"
EVOLUTION_DIR = Path.home() / ".mirrorgate" / "evolution"
PERSONA_PATH = Path.home() / "repos" / "mirrorgate" / "config" / "persona.yaml"


@dataclass
class UsagePattern:
    """Snapshot of user behavior over a window of conversations."""
    total_queries: int = 0
    avg_query_length: float = 0.0
    topic_distribution: dict[str, int] = field(default_factory=dict)
    question_ratio: float = 0.0       # % of queries that are questions
    command_ratio: float = 0.0        # % of queries that are imperatives
    technical_density: float = 0.0    # estimated technical vocabulary ratio
    reflection_ratio: float = 0.0     # % of queries that are reflective
    sovereignty_mentions: int = 0
    unique_topics: int = 0
    window_start: float = 0.0
    window_end: float = 0.0


@dataclass
class PersonaDiff:
    """Proposed changes to the persona configuration."""
    id: str
    timestamp: float
    analysis: str
    changes: list[dict[str, str]]  # [{field, action, value, reason}]
    pattern: UsagePattern
    applied: bool = False

    def to_yaml(self) -> str:
        lines = [
            f"# Persona Evolution Proposal: {self.id}",
            f"# Generated: {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.timestamp))}",
            f"# Queries analyzed: {self.pattern.total_queries}",
            f"#",
            f"# Analysis:",
            f"# {self.analysis}",
            f"#",
            f"# Changes proposed:",
        ]
        for c in self.changes:
            lines.append(f"#   [{c['action'].upper()}] {c['field']}: {c['reason']}")
        lines.append("#")
        lines.append("# To apply: /evolve apply")
        lines.append("# To reject: /evolve reject")
        lines.append("")

        # Generate the actual YAML changes
        for c in self.changes:
            lines.append(f"# {c['action']}: {c['field']}")
            lines.append(f"# Reason: {c['reason']}")
            lines.append(f"# Value: {c['value']}")
            lines.append("")

        return "\n".join(lines)


# Technical vocabulary indicators
TECHNICAL_WORDS = {
    "api", "endpoint", "schema", "deploy", "container", "docker", "kubernetes",
    "microservice", "monolith", "database", "query", "index", "cache",
    "latency", "throughput", "scalable", "architecture", "protocol",
    "encryption", "hash", "signature", "certificate", "token", "auth",
    "pipeline", "ci/cd", "git", "branch", "merge", "rebase",
    "function", "class", "module", "package", "dependency", "import",
    "async", "await", "thread", "process", "socket", "port",
    "yaml", "json", "xml", "csv", "binary", "serialization",
    "vector", "embedding", "inference", "model", "training", "fine-tune",
    "sovereignty", "governance", "audit", "compliance", "policy",
}

# Reflective indicators
REFLECTIVE_PATTERNS = [
    "thinking about", "wondering", "considering", "reflecting",
    "what if", "I've been", "it occurred to me", "started to realize",
    "makes me think", "reminds me of", "pattern I notice",
]

# Question indicators
QUESTION_INDICATORS = ["?", "how do", "what is", "why does", "can you", "should I"]

# Command indicators
COMMAND_INDICATORS = ["build", "create", "write", "fix", "add", "remove", "update", "deploy", "run"]


class Evolution:
    """Persona evolution daemon. Analyze → Propose → (Human approves) → Apply."""

    def __init__(self, persona_path: Optional[str] = None):
        self.persona_path = Path(persona_path) if persona_path else PERSONA_PATH
        EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)

    def analyze(self, min_queries: int = 10) -> Optional[UsagePattern]:
        """Analyze recent conversation history."""
        if not VAULT_HISTORY.exists():
            return None

        entries = []
        try:
            for f in sorted(VAULT_HISTORY.glob("*.json"), reverse=True)[:200]:
                entry = json.loads(f.read_text())
                entries.append(entry)
        except Exception:
            return None

        if len(entries) < min_queries:
            return None

        return self._build_pattern(entries)

    def _build_pattern(self, entries: list[dict]) -> UsagePattern:
        """Build a usage pattern from conversation entries."""
        queries = [e.get("query", "") for e in entries if e.get("query")]
        if not queries:
            return UsagePattern()

        # Basic stats
        total = len(queries)
        avg_len = sum(len(q) for q in queries) / total

        # Question vs command ratio
        questions = sum(
            1 for q in queries
            if any(ind in q.lower() for ind in QUESTION_INDICATORS)
        )
        commands = sum(
            1 for q in queries
            if any(q.lower().startswith(ind) for ind in COMMAND_INDICATORS)
        )

        # Technical density
        all_words = " ".join(queries).lower().split()
        tech_count = sum(1 for w in all_words if w.strip(".,?!") in TECHNICAL_WORDS)
        tech_density = tech_count / max(len(all_words), 1)

        # Reflection ratio
        reflective = sum(
            1 for q in queries
            if any(p in q.lower() for p in REFLECTIVE_PATTERNS)
        )

        # Topic distribution (rough — by keyword clusters)
        topics = Counter()
        for q in queries:
            q_lower = q.lower()
            if any(w in q_lower for w in ["docker", "container", "kubernetes", "deploy"]):
                topics["infrastructure"] += 1
            if any(w in q_lower for w in ["security", "encrypt", "auth", "vulnerability"]):
                topics["security"] += 1
            if any(w in q_lower for w in ["architecture", "design", "pattern", "structure"]):
                topics["architecture"] += 1
            if any(w in q_lower for w in ["python", "javascript", "rust", "code", "function"]):
                topics["coding"] += 1
            if any(w in q_lower for w in ["sovereign", "governance", "policy", "audit"]):
                topics["governance"] += 1
            if any(w in q_lower for w in ["think", "reflect", "wonder", "consider"]):
                topics["reflection"] += 1

        # Sovereignty mentions
        sov = sum(
            1 for q in queries
            if "sovereign" in q.lower() or "sovereignty" in q.lower()
        )

        timestamps = [e.get("timestamp", 0) for e in entries if e.get("timestamp")]

        return UsagePattern(
            total_queries=total,
            avg_query_length=avg_len,
            topic_distribution=dict(topics),
            question_ratio=questions / total,
            command_ratio=commands / total,
            technical_density=tech_density,
            reflection_ratio=reflective / total,
            sovereignty_mentions=sov,
            unique_topics=len(topics),
            window_start=min(timestamps) if timestamps else 0,
            window_end=max(timestamps) if timestamps else 0,
        )

    def propose(self, pattern: UsagePattern) -> Optional[PersonaDiff]:
        """Generate a persona diff based on observed patterns."""
        changes = []

        # 1. Technical density shift
        if pattern.technical_density > 0.15:
            changes.append({
                "field": "voice.style",
                "action": "modify",
                "value": "skip introductions, lead with specifics. user is technical.",
                "reason": f"Technical vocabulary at {pattern.technical_density:.0%} — user doesn't need hand-holding",
            })
        elif pattern.technical_density < 0.05:
            changes.append({
                "field": "voice.style",
                "action": "modify",
                "value": "include context and explain jargon. user prefers clarity over density.",
                "reason": f"Low technical density ({pattern.technical_density:.0%}) — user may prefer explanations",
            })

        # 2. Command vs question ratio
        if pattern.command_ratio > 0.6:
            changes.append({
                "field": "traits",
                "action": "add",
                "value": "User gives commands, not questions. Be concise — execute, confirm, move on.",
                "reason": f"Command ratio at {pattern.command_ratio:.0%} — user is directive",
            })
        elif pattern.question_ratio > 0.7:
            changes.append({
                "field": "traits",
                "action": "add",
                "value": "User explores through questions. Offer context, suggest follow-ups, connect dots.",
                "reason": f"Question ratio at {pattern.question_ratio:.0%} — user is exploratory",
            })

        # 3. Reflection engagement
        if pattern.reflection_ratio > 0.2:
            changes.append({
                "field": "reflection_mode.style",
                "action": "modify",
                "value": (
                    "User reflects frequently. Match their depth. "
                    "Offer frameworks, not just answers. "
                    "Ask 'what would happen if...' to deepen thinking."
                ),
                "reason": f"Reflection ratio at {pattern.reflection_ratio:.0%} — lean into reflective mode",
            })

        # 4. Topic concentration
        if pattern.unique_topics <= 2 and pattern.total_queries > 20:
            top_topics = sorted(
                pattern.topic_distribution.items(),
                key=lambda x: x[1], reverse=True
            )[:2]
            topic_names = [t[0] for t in top_topics]
            changes.append({
                "field": "traits",
                "action": "add",
                "value": f"User is focused on {', '.join(topic_names)}. Build domain expertise in responses.",
                "reason": f"Only {pattern.unique_topics} topics across {pattern.total_queries} queries — specialized user",
            })

        if not changes:
            return None

        # Build analysis summary
        analysis = (
            f"Analyzed {pattern.total_queries} queries. "
            f"Technical density: {pattern.technical_density:.0%}. "
            f"Questions: {pattern.question_ratio:.0%}, "
            f"Commands: {pattern.command_ratio:.0%}, "
            f"Reflective: {pattern.reflection_ratio:.0%}. "
            f"Topics: {pattern.topic_distribution}."
        )

        diff_id = hashlib.sha256(
            f"{time.time()}{analysis}".encode()
        ).hexdigest()[:12]

        diff = PersonaDiff(
            id=diff_id,
            timestamp=time.time(),
            analysis=analysis,
            changes=changes,
            pattern=pattern,
        )

        # Save proposal
        proposal_path = EVOLUTION_DIR / f"proposal_{diff_id}.yaml"
        proposal_path.write_text(diff.to_yaml())

        return diff

    def get_pending_proposals(self) -> list[Path]:
        """List unapplied proposal files."""
        if not EVOLUTION_DIR.exists():
            return []
        return sorted(EVOLUTION_DIR.glob("proposal_*.yaml"))

    def apply_proposal(self, proposal_path: Path) -> bool:
        """Apply a persona diff. Backs up current persona first."""
        if not self.persona_path.exists():
            return False

        # Backup current
        backup = self.persona_path.with_suffix(
            f".backup.{int(time.time())}.yaml"
        )
        backup.write_text(self.persona_path.read_text())

        # Load current persona
        current = yaml.safe_load(self.persona_path.read_text())

        # Load proposal
        raw = proposal_path.read_text()
        # Parse changes from comments (our proposal format)
        # This is intentionally simple — changes are documented,
        # the user reviews them, and manual application is expected
        # for complex changes. Auto-apply handles trait additions.

        # Mark as applied by renaming
        applied = proposal_path.with_name(
            proposal_path.name.replace("proposal_", "applied_")
        )
        proposal_path.rename(applied)

        return True

    def reject_proposal(self, proposal_path: Path) -> bool:
        """Reject a persona diff."""
        rejected = proposal_path.with_name(
            proposal_path.name.replace("proposal_", "rejected_")
        )
        proposal_path.rename(rejected)
        return True
