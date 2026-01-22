"""
Session Capture — Full action recording for replay

Captures:
- All actions with timestamps
- Decision points (alternatives considered)
- Confidence scores over time
- Permission state at each moment
- Gate results
"""

import json
import uuid as uuid_mod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum


class ContextMode(Enum):
    WORK = "work"
    REFLECT = "reflect"
    PLAY = "play"


@dataclass
class ActionRecord:
    """Record of a single action."""
    action_id: str
    timestamp: str
    action_type: str
    target: str
    content_preview: str  # First 100 chars
    result: str  # ALLOW, BLOCK, REWRITE
    confidence: float
    gate_results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionPoint:
    """Record of a significant decision."""
    decision_id: str
    timestamp: str
    action_id: str  # Related action
    alternatives: List[str]
    chosen: str
    rationale: str
    confidence: float


@dataclass
class PermissionSnapshot:
    """Permission state at a moment."""
    timestamp: str
    active_permissions: List[Dict[str, Any]]
    context_mode: str


@dataclass
class SessionMetrics:
    """Metrics for a session."""
    total_actions: int = 0
    blocked_actions: int = 0
    rewrites: int = 0
    tripwires_triggered: int = 0
    avg_confidence: float = 0.0


@dataclass
class Session:
    """Full session record."""
    session_id: str
    started_at: str
    ended_at: Optional[str]
    actor: str
    context_mode: str
    actions: List[ActionRecord] = field(default_factory=list)
    decision_points: List[DecisionPoint] = field(default_factory=list)
    permission_snapshots: List[PermissionSnapshot] = field(default_factory=list)
    metrics: SessionMetrics = field(default_factory=SessionMetrics)


FORENSICS_DIR = Path.home() / ".mirrordna" / "forensics"
SESSIONS_DIR = FORENSICS_DIR / "sessions"


class SessionCapture:
    """
    Captures full session for later replay.
    """
    
    def __init__(self, actor: str = "agent", context_mode: str = "work"):
        self.session = Session(
            session_id=str(uuid_mod.uuid4()),
            started_at=datetime.now(timezone.utc).isoformat(),
            ended_at=None,
            actor=actor,
            context_mode=context_mode
        )
        self._confidence_sum = 0.0
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Create directories."""
        today = datetime.now().strftime("%Y-%m-%d")
        (SESSIONS_DIR / today).mkdir(parents=True, exist_ok=True)
    
    @property
    def session_id(self) -> str:
        return self.session.session_id
    
    def record_action(
        self,
        action_type: str,
        target: str,
        content: str,
        result: str,
        confidence: float = 0.8,
        gate_results: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Record an action."""
        action_id = str(uuid_mod.uuid4())
        
        record = ActionRecord(
            action_id=action_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action_type,
            target=target,
            content_preview=content[:100] if content else "",
            result=result,
            confidence=confidence,
            gate_results=gate_results or [],
            metadata=metadata or {}
        )
        
        self.session.actions.append(record)
        
        # Update metrics
        self.session.metrics.total_actions += 1
        if result == "BLOCK":
            self.session.metrics.blocked_actions += 1
        elif result == "REWRITE":
            self.session.metrics.rewrites += 1
        
        self._confidence_sum += confidence
        self.session.metrics.avg_confidence = (
            self._confidence_sum / self.session.metrics.total_actions
        )
        
        return action_id
    
    def record_decision_point(
        self,
        action_id: str,
        alternatives: List[str],
        chosen: str,
        rationale: str,
        confidence: float = 0.8
    ) -> str:
        """Record a decision point."""
        decision_id = str(uuid_mod.uuid4())
        
        decision = DecisionPoint(
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_id=action_id,
            alternatives=alternatives,
            chosen=chosen,
            rationale=rationale,
            confidence=confidence
        )
        
        self.session.decision_points.append(decision)
        return decision_id
    
    def snapshot_permissions(
        self,
        active_permissions: List[Dict],
        context_mode: str
    ):
        """Take a permission snapshot."""
        snapshot = PermissionSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            active_permissions=active_permissions,
            context_mode=context_mode
        )
        self.session.permission_snapshots.append(snapshot)
    
    def record_tripwire(self, tripwire_type: str, details: Dict):
        """Record a tripwire trigger."""
        self.session.metrics.tripwires_triggered += 1
        # Add to most recent action's metadata
        if self.session.actions:
            self.session.actions[-1].metadata["tripwire"] = {
                "type": tripwire_type,
                **details
            }
    
    def end_session(self) -> str:
        """End session and save to disk."""
        self.session.ended_at = datetime.now(timezone.utc).isoformat()
        
        # Save to file
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = SESSIONS_DIR / today / f"session-{self.session.session_id}.json"
        
        session_dict = self._to_dict(self.session)
        
        with open(session_file, 'w') as f:
            json.dump(session_dict, f, indent=2, default=str)
        
        return str(session_file)
    
    def _to_dict(self, obj) -> Dict:
        """Convert dataclass to dict recursively."""
        if hasattr(obj, '__dataclass_fields__'):
            return {k: self._to_dict(v) for k, v in asdict(obj).items()}
        elif isinstance(obj, list):
            return [self._to_dict(i) for i in obj]
        elif isinstance(obj, Enum):
            return obj.value
        return obj
    
    def get_session_data(self) -> Dict:
        """Get session data without saving."""
        return self._to_dict(self.session)


# Global session tracker
_current_session: Optional[SessionCapture] = None


def begin_session(actor: str = "agent", context_mode: str = "work") -> SessionCapture:
    """Begin a new capture session."""
    global _current_session
    _current_session = SessionCapture(actor=actor, context_mode=context_mode)
    return _current_session


def end_session() -> Optional[str]:
    """End current session and return file path."""
    global _current_session
    if _current_session:
        path = _current_session.end_session()
        _current_session = None
        return path
    return None


def get_current_session() -> Optional[SessionCapture]:
    """Get current session if active."""
    return _current_session
