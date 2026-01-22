"""
Session Replay — Reconstruct session state at any point

Capabilities:
- Load session by ID
- Step through actions
- View decision tree
- Show permission state at each moment
- Reconstruct world view at decision time
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterator


FORENSICS_DIR = Path.home() / ".mirrordna" / "forensics"
SESSIONS_DIR = FORENSICS_DIR / "sessions"


@dataclass
class ReplayState:
    """State at a point in session."""
    action_index: int
    timestamp: str
    action: Dict[str, Any]
    cumulative_metrics: Dict[str, int]
    permission_state: Optional[Dict] = None
    decision_at_action: Optional[Dict] = None


class SessionReplay:
    """
    Replays a captured session for analysis.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_data = self._load_session()
        self._current_index = 0
    
    def _load_session(self) -> Dict:
        """Find and load session file."""
        # Search all date directories
        for date_dir in SESSIONS_DIR.iterdir():
            if date_dir.is_dir():
                session_file = date_dir / f"session-{self.session_id}.json"
                if session_file.exists():
                    with open(session_file, 'r') as f:
                        return json.load(f)
        
        raise FileNotFoundError(f"Session not found: {self.session_id}")
    
    @property
    def total_actions(self) -> int:
        return len(self.session_data.get("actions", []))
    
    @property
    def actions(self) -> List[Dict]:
        return self.session_data.get("actions", [])
    
    @property
    def decision_points(self) -> List[Dict]:
        return self.session_data.get("decision_points", [])
    
    @property
    def metrics(self) -> Dict:
        return self.session_data.get("metrics", {})
    
    def reset(self):
        """Reset replay to beginning."""
        self._current_index = 0
    
    def step(self) -> Optional[ReplayState]:
        """Step forward one action."""
        if self._current_index >= self.total_actions:
            return None
        
        action = self.actions[self._current_index]
        
        # Calculate cumulative metrics up to this point
        actions_so_far = self.actions[:self._current_index + 1]
        cumulative = {
            "total": len(actions_so_far),
            "blocked": sum(1 for a in actions_so_far if a.get("result") == "BLOCK"),
            "rewrites": sum(1 for a in actions_so_far if a.get("result") == "REWRITE"),
        }
        
        # Find permission state at this time
        perm_state = None
        action_time = action.get("timestamp", "")
        for snapshot in self.session_data.get("permission_snapshots", []):
            if snapshot.get("timestamp", "") <= action_time:
                perm_state = snapshot
        
        # Find decision point for this action
        decision = None
        action_id = action.get("action_id")
        for dp in self.decision_points:
            if dp.get("action_id") == action_id:
                decision = dp
                break
        
        state = ReplayState(
            action_index=self._current_index,
            timestamp=action_time,
            action=action,
            cumulative_metrics=cumulative,
            permission_state=perm_state,
            decision_at_action=decision
        )
        
        self._current_index += 1
        return state
    
    def goto(self, index: int) -> Optional[ReplayState]:
        """Go to specific action index."""
        if 0 <= index < self.total_actions:
            self._current_index = index
            return self.step()
        return None
    
    def iter_actions(self) -> Iterator[ReplayState]:
        """Iterate through all actions."""
        self.reset()
        while True:
            state = self.step()
            if state is None:
                break
            yield state
    
    def find_action(self, action_id: str) -> Optional[ReplayState]:
        """Find action by ID."""
        for i, action in enumerate(self.actions):
            if action.get("action_id") == action_id:
                return self.goto(i)
        return None
    
    def get_world_view(self, action_index: int) -> Dict[str, Any]:
        """
        Reconstruct "world view" at a specific action.
        
        This is the 2050 Audit requirement: what was known at decision time.
        """
        if action_index >= self.total_actions:
            action_index = self.total_actions - 1
        
        action = self.actions[action_index]
        
        # What was known
        actions_before = self.actions[:action_index]
        
        # Permissions at that time
        perm_state = None
        action_time = action.get("timestamp", "")
        for snapshot in self.session_data.get("permission_snapshots", []):
            if snapshot.get("timestamp", "") <= action_time:
                perm_state = snapshot
        
        # Decisions made before
        prior_decisions = [
            dp for dp in self.decision_points
            if dp.get("timestamp", "") < action_time
        ]
        
        # Gate results
        gate_results = action.get("gate_results", [])
        
        return {
            "action": action,
            "action_index": action_index,
            "session_context": {
                "mode": self.session_data.get("context_mode"),
                "actor": self.session_data.get("actor"),
                "started_at": self.session_data.get("started_at")
            },
            "what_was_known": {
                "prior_actions": len(actions_before),
                "prior_decisions": len(prior_decisions),
                "blocked_so_far": sum(1 for a in actions_before if a.get("result") == "BLOCK")
            },
            "permission_state": perm_state,
            "gate_results": gate_results,
            "reasoning": action.get("metadata", {}).get("reasoning", "Not recorded"),
            "confidence": action.get("confidence", 0)
        }
    
    def get_decision_tree(self) -> Dict[str, Any]:
        """Get decision tree visualization data."""
        nodes = []
        edges = []
        
        for i, action in enumerate(self.actions):
            action_id = action.get("action_id")
            nodes.append({
                "id": action_id,
                "type": "action",
                "label": f"{action.get('action_type')}",
                "result": action.get("result"),
                "index": i
            })
            
            # Find if there's a decision point
            for dp in self.decision_points:
                if dp.get("action_id") == action_id:
                    dp_id = dp.get("decision_id")
                    nodes.append({
                        "id": dp_id,
                        "type": "decision",
                        "label": "Decision",
                        "alternatives": dp.get("alternatives", []),
                        "chosen": dp.get("chosen")
                    })
                    edges.append({"from": action_id, "to": dp_id})
            
            # Link sequential actions
            if i > 0:
                prev_id = self.actions[i-1].get("action_id")
                edges.append({"from": prev_id, "to": action_id})
        
        return {"nodes": nodes, "edges": edges}


def list_sessions(date: Optional[str] = None) -> List[Dict]:
    """List available sessions."""
    sessions = []
    
    dirs = [SESSIONS_DIR / date] if date else list(SESSIONS_DIR.iterdir())
    
    for date_dir in dirs:
        if date_dir.is_dir():
            for session_file in date_dir.glob("session-*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                        sessions.append({
                            "session_id": data.get("session_id"),
                            "started_at": data.get("started_at"),
                            "ended_at": data.get("ended_at"),
                            "actor": data.get("actor"),
                            "total_actions": data.get("metrics", {}).get("total_actions", 0),
                            "file": str(session_file)
                        })
                except Exception:
                    continue
    
    return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)
