"""
Pydantic schemas for the Hypervisor pipeline.

These define the exact shape of structured LLM output.
The `response` field carries the persona's voice.
Everything else is auditable metadata.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class IntentClass(str, Enum):
    TECHNICAL = "technical_architectural"
    PHILOSOPHICAL = "philosophical"
    CASUAL = "casual"
    CREATIVE = "creative"
    SOVEREIGN = "sovereign_governance"


class SovereigntyStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class RiskLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Meta(BaseModel):
    """Classification metadata for the query."""
    intent: IntentClass = Field(
        description="What kind of query this is"
    )
    complexity: float = Field(
        ge=0.0, le=1.0,
        description="How complex the reasoning required is, 0-1"
    )


class CognitiveTrace(BaseModel):
    """The reasoning chain — auditable thought process."""
    reasoning: str = Field(
        description="Step-by-step reasoning about the query"
    )
    conflict: Optional[str] = Field(
        default=None,
        description="Any tension between competing goals or constraints"
    )
    resolution: Optional[str] = Field(
        default=None,
        description="How the conflict was resolved, if any"
    )


class Inference(BaseModel):
    """The core analytical output."""
    answer: str = Field(
        description="Direct, factual answer to the query"
    )
    code_snippet: Optional[str] = Field(
        default=None,
        description="Code block if relevant"
    )
    code_language: Optional[str] = Field(
        default=None,
        description="Language of the code snippet (python, yaml, bash, etc.)"
    )
    technical_depth: str = Field(
        default="medium",
        description="low, medium, or high"
    )


class SovereigntyAudit(BaseModel):
    """Self-reported sovereignty assessment.
    NOTE: The Auditor independently validates this. Do not trust blindly.
    """
    status: SovereigntyStatus = Field(
        description="Whether the response respects sovereignty constraints"
    )
    risk: RiskLevel = Field(
        default=RiskLevel.NONE,
        description="Risk level of the suggested approach"
    )
    warning: Optional[str] = Field(
        default=None,
        description="Debt warning if sovereignty is compromised"
    )


class HypervisorOutput(BaseModel):
    """Full structured output from the Hypervisor Core (L2).

    The `response` field is the conversational output with persona.
    All other fields are auditable metadata.
    """
    meta: Meta
    trace: CognitiveTrace
    inference: Inference
    sovereignty: SovereigntyAudit
    response: str = Field(
        description=(
            "The conversational response to the user. "
            "This is the primary output. Write with character and voice — "
            "not bland, not robotic. Reflect the persona's perspective."
        )
    )
    next_action: Optional[str] = Field(
        default=None,
        description="Suggested next step, if any"
    )


class AuditVerdict(BaseModel):
    """Output of the independent Auditor (L3)."""
    passed: bool
    flags: list[str] = Field(default_factory=list)
    overrides: dict[str, str] = Field(default_factory=dict)
    risk_score: float = Field(ge=0.0, le=1.0, default=0.0)


class VaultContext(BaseModel):
    """Context assembled by the Vault (L1) before inference."""
    facts: list[str] = Field(default_factory=list)
    memory: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
