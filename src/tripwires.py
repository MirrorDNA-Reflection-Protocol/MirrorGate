"""
Tripwires — Behavioral Pattern Detection

Detects patterns over time, not just individual actions.

Tripwires:
- Drift detection: behavior vs baseline
- Autonomy creep: self_initiated / total ratio
- Scope expansion: new areas accessed without prompt
- Confidence collapse: low-confidence streak
- Loop detection: repeated similar actions
"""

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml


class TripwireType(Enum):
    DRIFT = "drift"
    AUTONOMY_CREEP = "autonomy_creep"
    SCOPE_EXPANSION = "scope_expansion"
    CONFIDENCE_COLLAPSE = "confidence_collapse"
    LOOP_DETECTION = "loop_detection"


class TripwireResponse(Enum):
    ALERT = "alert"
    LOG = "log"
    ESCALATE = "escalate"
    SOFT_BLOCK = "soft_block"
    PAUSE = "pause"
    INTERRUPT = "interrupt"


@dataclass
class TripwireConfig:
    """Configuration for a tripwire."""
    tripwire_type: TripwireType
    threshold: Any
    response: TripwireResponse
    window_minutes: int = 60  # Rolling window
    enabled: bool = True


@dataclass
class TripwireEvent:
    """A triggered tripwire event."""
    tripwire_type: TripwireType
    triggered_at: datetime
    threshold: Any
    actual_value: Any
    response: TripwireResponse
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionRecord:
    """Record of an action for pattern analysis."""
    timestamp: datetime
    action_type: str
    target: str
    confidence: float
    initiated_by: str  # "user" or "self"
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


TRIPWIRE_CONFIG = Path.home() / ".mirrordna" / "oversight" / "tripwires.yaml"
BASELINE_DIR = Path.home() / ".mirrordna" / "oversight" / "baselines"
METRICS_DIR = Path.home() / ".mirrordna" / "oversight" / "metrics"


class TripwireSystem:
    """
    Behavioral pattern detection system.
    Tracks actions over rolling windows and detects anomalies.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or TRIPWIRE_CONFIG
        self.configs: List[TripwireConfig] = []
        
        # Rolling action history (configurable window)
        self.action_history: deque = deque(maxlen=1000)
        
        # Baseline metrics (loaded on init)
        self.baseline: Dict[str, Any] = {}
        
        # Current session metrics
        self.session_metrics: Dict[str, Any] = {
            "actions_total": 0,
            "actions_self_initiated": 0,
            "unique_targets": set(),
            "confidence_scores": [],
            "action_hashes": [],  # For loop detection
            "low_confidence_streak": 0
        }
        
        self._load_config()
        self._load_baseline()
    
    def _load_config(self):
        """Load tripwire configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                
                for tw_data in data.get("tripwires", []):
                    self.configs.append(TripwireConfig(
                        tripwire_type=TripwireType(tw_data.get("type")),
                        threshold=tw_data.get("threshold"),
                        response=TripwireResponse(tw_data.get("response", "log")),
                        window_minutes=tw_data.get("window_minutes", 60),
                        enabled=tw_data.get("enabled", True)
                    ))
            except Exception as e:
                print(f"Warning: Failed to load tripwire config: {e}")
        
        # Add defaults if no config
        if not self.configs:
            self.configs = self._default_configs()
    
    def _default_configs(self) -> List[TripwireConfig]:
        """Default tripwire configurations per spec."""
        return [
            TripwireConfig(
                tripwire_type=TripwireType.DRIFT,
                threshold=0.3,  # 30% deviation from baseline
                response=TripwireResponse.ALERT,
                window_minutes=60
            ),
            TripwireConfig(
                tripwire_type=TripwireType.AUTONOMY_CREEP,
                threshold=0.4,  # 40% self-initiated
                response=TripwireResponse.ESCALATE,
                window_minutes=60
            ),
            TripwireConfig(
                tripwire_type=TripwireType.SCOPE_EXPANSION,
                threshold=1,  # Any new area without prompt
                response=TripwireResponse.SOFT_BLOCK,
                window_minutes=60
            ),
            TripwireConfig(
                tripwire_type=TripwireType.CONFIDENCE_COLLAPSE,
                threshold=5,  # 5 consecutive low-confidence
                response=TripwireResponse.PAUSE,
                window_minutes=60
            ),
            TripwireConfig(
                tripwire_type=TripwireType.LOOP_DETECTION,
                threshold=3,  # 3 repeated similar actions
                response=TripwireResponse.INTERRUPT,
                window_minutes=15
            ),
        ]
    
    def _load_baseline(self):
        """Load behavioral baseline from file."""
        baseline_file = BASELINE_DIR / "baseline.json"
        if baseline_file.exists():
            try:
                with open(baseline_file, 'r') as f:
                    self.baseline = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load baseline: {e}")
                self.baseline = {}
        else:
            # Initialize empty baseline
            self.baseline = {
                "avg_actions_per_hour": 0,
                "common_targets": [],
                "avg_confidence": 0.8,
                "self_initiated_ratio": 0.2,
                "sessions_sampled": 0
            }
    
    def save_baseline(self):
        """Save current session metrics to baseline."""
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        baseline_file = BASELINE_DIR / "baseline.json"
        
        # Update baseline with current session (weighted average)
        sessions = self.baseline.get("sessions_sampled", 0)
        
        if sessions > 0:
            # Weighted update
            weight = 1 / (sessions + 1)
            
            if self.session_metrics["actions_total"] > 0:
                current_ratio = (
                    self.session_metrics["actions_self_initiated"] / 
                    self.session_metrics["actions_total"]
                )
                self.baseline["self_initiated_ratio"] = (
                    self.baseline.get("self_initiated_ratio", 0) * (1 - weight) +
                    current_ratio * weight
                )
            
            if self.session_metrics["confidence_scores"]:
                avg_conf = sum(self.session_metrics["confidence_scores"]) / len(self.session_metrics["confidence_scores"])
                self.baseline["avg_confidence"] = (
                    self.baseline.get("avg_confidence", 0.8) * (1 - weight) +
                    avg_conf * weight
                )
        else:
            # First session - initialize
            if self.session_metrics["actions_total"] > 0:
                self.baseline["self_initiated_ratio"] = (
                    self.session_metrics["actions_self_initiated"] / 
                    self.session_metrics["actions_total"]
                )
            if self.session_metrics["confidence_scores"]:
                self.baseline["avg_confidence"] = (
                    sum(self.session_metrics["confidence_scores"]) / 
                    len(self.session_metrics["confidence_scores"])
                )
        
        self.baseline["sessions_sampled"] = sessions + 1
        self.baseline["common_targets"] = list(self.session_metrics["unique_targets"])[:20]
        
        try:
            with open(baseline_file, 'w') as f:
                json.dump(self.baseline, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Failed to save baseline: {e}")
    
    def record_action(self, action: ActionRecord) -> List[TripwireEvent]:
        """
        Record an action and check for tripwire triggers.
        Returns list of triggered events.
        """
        # Add to history
        self.action_history.append(action)
        
        # Update session metrics
        self.session_metrics["actions_total"] += 1
        if action.initiated_by == "self":
            self.session_metrics["actions_self_initiated"] += 1
        
        self.session_metrics["unique_targets"].add(action.target)
        self.session_metrics["confidence_scores"].append(action.confidence)
        
        # Track confidence streak
        if action.confidence < 0.5:
            self.session_metrics["low_confidence_streak"] += 1
        else:
            self.session_metrics["low_confidence_streak"] = 0
        
        # Track action hash for loop detection
        action_hash = f"{action.action_type}:{action.target}"
        self.session_metrics["action_hashes"].append(action_hash)
        
        # Check tripwires
        return self.check_tripwires()
    
    def check_tripwires(self) -> List[TripwireEvent]:
        """Check all enabled tripwires against current state."""
        triggered = []
        
        for config in self.configs:
            if not config.enabled:
                continue
            
            event = self._check_single_tripwire(config)
            if event:
                triggered.append(event)
                self._log_tripwire_event(event)
        
        return triggered
    
    def _check_single_tripwire(self, config: TripwireConfig) -> Optional[TripwireEvent]:
        """Check a single tripwire."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=config.window_minutes)
        
        # Get actions in window
        recent_actions = [
            a for a in self.action_history 
            if a.timestamp >= window_start
        ]
        
        if config.tripwire_type == TripwireType.AUTONOMY_CREEP:
            return self._check_autonomy_creep(config, recent_actions)
        
        elif config.tripwire_type == TripwireType.CONFIDENCE_COLLAPSE:
            return self._check_confidence_collapse(config)
        
        elif config.tripwire_type == TripwireType.LOOP_DETECTION:
            return self._check_loop_detection(config)
        
        elif config.tripwire_type == TripwireType.SCOPE_EXPANSION:
            return self._check_scope_expansion(config, recent_actions)
        
        elif config.tripwire_type == TripwireType.DRIFT:
            return self._check_drift(config, recent_actions)
        
        return None
    
    def _check_autonomy_creep(
        self, 
        config: TripwireConfig, 
        recent_actions: List[ActionRecord]
    ) -> Optional[TripwireEvent]:
        """Check for too many self-initiated actions."""
        if len(recent_actions) < 5:  # Need minimum sample
            return None
        
        self_initiated = sum(1 for a in recent_actions if a.initiated_by == "self")
        ratio = self_initiated / len(recent_actions)
        
        if ratio > config.threshold:
            return TripwireEvent(
                tripwire_type=TripwireType.AUTONOMY_CREEP,
                triggered_at=datetime.now(timezone.utc),
                threshold=config.threshold,
                actual_value=ratio,
                response=config.response,
                message=f"Autonomy ratio {ratio:.1%} exceeds threshold {config.threshold:.0%}",
                context={
                    "self_initiated": self_initiated,
                    "total": len(recent_actions)
                }
            )
        return None
    
    def _check_confidence_collapse(self, config: TripwireConfig) -> Optional[TripwireEvent]:
        """Check for streak of low-confidence actions."""
        streak = self.session_metrics["low_confidence_streak"]
        
        if streak >= config.threshold:
            return TripwireEvent(
                tripwire_type=TripwireType.CONFIDENCE_COLLAPSE,
                triggered_at=datetime.now(timezone.utc),
                threshold=config.threshold,
                actual_value=streak,
                response=config.response,
                message=f"Low confidence streak: {streak} consecutive actions below 50%",
                context={"streak": streak}
            )
        return None
    
    def _check_loop_detection(self, config: TripwireConfig) -> Optional[TripwireEvent]:
        """Check for repeated similar actions."""
        action_hashes = self.session_metrics["action_hashes"]
        if len(action_hashes) < config.threshold:
            return None
        
        # Check last N actions for repetition
        recent = action_hashes[-10:]
        for action in set(recent):
            count = recent.count(action)
            if count >= config.threshold:
                return TripwireEvent(
                    tripwire_type=TripwireType.LOOP_DETECTION,
                    triggered_at=datetime.now(timezone.utc),
                    threshold=config.threshold,
                    actual_value=count,
                    response=config.response,
                    message=f"Loop detected: '{action}' repeated {count} times",
                    context={"action": action, "count": count}
                )
        return None
    
    def _check_scope_expansion(
        self,
        config: TripwireConfig,
        recent_actions: List[ActionRecord]
    ) -> Optional[TripwireEvent]:
        """Check for access to new areas without prompt."""
        if not self.baseline.get("common_targets"):
            return None  # No baseline yet
        
        common = set(self.baseline["common_targets"])
        new_targets = []
        
        for action in recent_actions:
            if action.initiated_by == "self" and action.target not in common:
                new_targets.append(action.target)
        
        if len(new_targets) >= config.threshold:
            return TripwireEvent(
                tripwire_type=TripwireType.SCOPE_EXPANSION,
                triggered_at=datetime.now(timezone.utc),
                threshold=config.threshold,
                actual_value=len(new_targets),
                response=config.response,
                message=f"Scope expansion: {len(new_targets)} new areas accessed without prompt",
                context={"new_targets": new_targets[:5]}
            )
        return None
    
    def _check_drift(
        self,
        config: TripwireConfig,
        recent_actions: List[ActionRecord]
    ) -> Optional[TripwireEvent]:
        """Check for behavioral drift from baseline."""
        if not self.baseline or self.baseline.get("sessions_sampled", 0) < 3:
            return None  # Need baseline
        
        if len(recent_actions) < 10:
            return None  # Need sample
        
        # Compare self-initiated ratio
        current_self_ratio = (
            sum(1 for a in recent_actions if a.initiated_by == "self") /
            len(recent_actions)
        )
        baseline_ratio = self.baseline.get("self_initiated_ratio", 0.2)
        
        drift = abs(current_self_ratio - baseline_ratio)
        
        if drift > config.threshold:
            return TripwireEvent(
                tripwire_type=TripwireType.DRIFT,
                triggered_at=datetime.now(timezone.utc),
                threshold=config.threshold,
                actual_value=drift,
                response=config.response,
                message=f"Behavioral drift: {drift:.1%} deviation from baseline",
                context={
                    "current_ratio": current_self_ratio,
                    "baseline_ratio": baseline_ratio
                }
            )
        return None
    
    def _log_tripwire_event(self, event: TripwireEvent):
        """Log tripwire event to metrics directory."""
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        
        log_file = METRICS_DIR / f"tripwire_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        record = {
            "type": event.tripwire_type.value,
            "triggered_at": event.triggered_at.isoformat(),
            "threshold": event.threshold,
            "actual": event.actual_value,
            "response": event.response.value,
            "message": event.message,
            "context": event.context
        }
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as e:
            print(f"Warning: Failed to log tripwire event: {e}")
