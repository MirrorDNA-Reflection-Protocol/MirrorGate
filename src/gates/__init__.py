"""
MirrorGate Gate Chain
⟡ The LLM never decides. Gates decide.

Gate sequence:
- Gate 0: Transport & Rate Control
- Gate 1: Semantic Classifier (existing in classifiers/)
- Gate 2: Content Filter (existing in rules.py)
- Gate 3: Prompt Injection Detection
- Gate 4: Size & Complexity Limits
- Gate 5: Intent Classification & Routing
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import time


class GateResult(Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    REPLAY_REJECTED = "REPLAY_REJECTED"
    SESSION_INVALID = "SESSION_INVALID"
    INJECTION_BLOCKED = "INJECTION_BLOCKED"
    TOO_LARGE = "TOO_LARGE"
    TOO_COMPLEX = "TOO_COMPLEX"
    REPETITIVE = "REPETITIVE"


class IntentMode(Enum):
    TRANSACTIONAL = "TRANSACTIONAL"
    REFLECTIVE = "REFLECTIVE"
    PLAY = "PLAY"


@dataclass
class GateOutput:
    """Output from a single gate."""
    gate_name: str
    result: GateResult
    violations: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    processing_time_ms: float = 0.0


@dataclass
class GateChainResult:
    """Result from running the full gate chain."""
    allowed: bool
    gate_results: list  # List of GateOutput
    mode: Optional[IntentMode] = None
    confidence: float = 0.0
    total_time_ms: float = 0.0
    blocked_by: Optional[str] = None


def run_gates(request: dict, session_token: Optional[str] = None) -> GateChainResult:
    """
    Run all gates in sequence.
    
    Args:
        request: The incoming request with 'content' and optional metadata
        session_token: Optional session token for validation
        
    Returns:
        GateChainResult with allowed status, all gate results, and routing mode
    """
    from .gate0_transport import Gate0Transport
    from .gate3_injection import Gate3Injection
    from .gate4_complexity import Gate4Complexity
    from .gate5_intent import Gate5Intent
    
    start = time.perf_counter()
    gate_results = []
    
    # Initialize gates
    gates = [
        Gate0Transport(),
        Gate3Injection(),
        Gate4Complexity(),
        Gate5Intent(),
    ]
    
    # Run gate chain
    mode = None
    confidence = 0.0
    blocked_by = None
    
    for gate in gates:
        gate_start = time.perf_counter()
        
        output = gate.evaluate(request, session_token)
        output.processing_time_ms = (time.perf_counter() - gate_start) * 1000
        gate_results.append(output)
        
        # Check for blocking result
        if output.result != GateResult.PASS:
            if output.result != GateResult.PASS and gate.is_blocking:
                blocked_by = output.gate_name
                return GateChainResult(
                    allowed=False,
                    gate_results=gate_results,
                    total_time_ms=(time.perf_counter() - start) * 1000,
                    blocked_by=blocked_by
                )
        
        # Capture intent mode from Gate 5
        if output.gate_name == "Gate5_Intent" and output.metadata.get("mode"):
            mode = IntentMode(output.metadata["mode"])
            confidence = output.metadata.get("confidence", 0.0)
    
    total_time = (time.perf_counter() - start) * 1000
    
    return GateChainResult(
        allowed=True,
        gate_results=gate_results,
        mode=mode,
        confidence=confidence,
        total_time_ms=total_time
    )


class BaseGate:
    """Base class for all gates."""
    
    name: str = "BaseGate"
    is_blocking: bool = True  # If True, failure stops the chain
    
    def evaluate(self, request: dict, session_token: Optional[str] = None) -> GateOutput:
        """Evaluate the request against this gate's rules."""
        raise NotImplementedError
