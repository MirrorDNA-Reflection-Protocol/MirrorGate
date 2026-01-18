"""
DBB Generator — Decisional Black Box sidecar files

Per DBB v1.0 spec, generates JSON-LD sidecar files for significant decisions.

Schema:
- Decision_ID: UUID-v4
- Temporal_Anchor: ISO-8601 + Unix Epoch
- System_State: Core model, context hash
- Reasoning_Trace: Chain of thought
- Evidence_Nodes: Vault file references
- Steward_Signoff: Manual verification flag
"""

import json
import hashlib
import uuid as uuid_mod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class SystemState:
    """System state at decision time."""
    core_model: str  # Active model
    active_context_hash: str  # SHA-256 of loaded context
    policy_hash: str  # Current policy hash
    gate_chain_version: str
    rules_version: str


@dataclass
class EvidenceNode:
    """Reference to evidence in vault."""
    source_type: str  # "vault_file", "session", "audit_log"
    reference: str  # Path or ID
    hash: str  # SHA-256 of content at decision time
    excerpt: str  # Relevant portion


@dataclass
class DBBRecord:
    """Decisional Black Box record."""
    # Core fields
    decision_id: str
    temporal_anchor: Dict[str, Any]  # ISO-8601 + Unix epoch
    version: str = "1.0"
    
    # Context
    system_state: Optional[SystemState] = None
    session_id: Optional[str] = None
    action_id: Optional[str] = None
    
    # Decision content
    decision_type: str = ""  # ALLOW, BLOCK, REWRITE, ESCALATE
    target: str = ""
    reasoning_trace: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    
    # Evidence
    evidence_nodes: List[EvidenceNode] = field(default_factory=list)
    confidence: float = 0.0
    
    # Verification
    steward_signoff: bool = False
    signoff_timestamp: Optional[str] = None
    signoff_by: Optional[str] = None
    
    # Chain linking
    supersedes: Optional[str] = None  # Previous decision ID if this is an update
    chain_hash: Optional[str] = None


DBB_DIR = Path.home() / ".mirrordna" / "dbb"


class DBBGenerator:
    """
    Generates DBB sidecar files for significant decisions.
    """
    
    def __init__(self):
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Create DBB directory structure."""
        today = datetime.now().strftime("%Y-%m-%d")
        (DBB_DIR / today).mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        decision_type: str,
        target: str,
        reasoning_trace: List[str],
        system_state: Optional[SystemState] = None,
        session_id: Optional[str] = None,
        action_id: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        evidence: Optional[List[EvidenceNode]] = None,
        confidence: float = 0.8,
        supersedes: Optional[str] = None
    ) -> str:
        """
        Generate a DBB sidecar file.
        
        Returns: Path to generated .dbb file
        """
        now = datetime.now(timezone.utc)
        decision_id = str(uuid_mod.uuid4())
        
        record = DBBRecord(
            decision_id=decision_id,
            temporal_anchor={
                "iso8601": now.isoformat(),
                "unix_epoch": now.timestamp(),
                "timezone": "UTC"
            },
            system_state=system_state,
            session_id=session_id,
            action_id=action_id,
            decision_type=decision_type,
            target=target,
            reasoning_trace=reasoning_trace,
            alternatives_considered=alternatives or [],
            evidence_nodes=evidence or [],
            confidence=confidence,
            supersedes=supersedes
        )
        
        # Compute chain hash
        record_json = json.dumps(self._to_dict(record), sort_keys=True)
        record.chain_hash = hashlib.sha256(record_json.encode()).hexdigest()
        
        # Save to file
        today = now.strftime("%Y-%m-%d")
        dbb_file = DBB_DIR / today / f"decision-{decision_id}.dbb"
        
        # Write as JSON-LD (simplified)
        output = {
            "@context": "https://mirrorgate.ai/dbb/v1",
            "@type": "DecisionalBlackBox",
            **self._to_dict(record)
        }
        
        with open(dbb_file, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        return str(dbb_file)
    
    def signoff(
        self,
        decision_id: str,
        signoff_by: str = "paul"
    ) -> bool:
        """
        Add steward signoff to a DBB record.
        Creates new record with signoff, linking to original.
        """
        # Find the original file
        original = self._find_decision(decision_id)
        if not original:
            return False
        
        # Load original
        with open(original, 'r') as f:
            data = json.load(f)
        
        # Create signoff update
        now = datetime.now(timezone.utc)
        new_id = str(uuid_mod.uuid4())
        
        data["steward_signoff"] = True
        data["signoff_timestamp"] = now.isoformat()
        data["signoff_by"] = signoff_by
        data["supersedes"] = decision_id
        data["decision_id"] = new_id
        
        # Recompute chain hash
        del data["@context"]
        del data["@type"]
        data["chain_hash"] = None
        record_json = json.dumps(data, sort_keys=True)
        data["chain_hash"] = hashlib.sha256(record_json.encode()).hexdigest()
        
        # Save new file
        today = now.strftime("%Y-%m-%d")
        dbb_file = DBB_DIR / today / f"decision-{new_id}.dbb"
        
        output = {
            "@context": "https://mirrorgate.ai/dbb/v1",
            "@type": "DecisionalBlackBox",
            **data
        }
        
        with open(dbb_file, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        return True
    
    def _find_decision(self, decision_id: str) -> Optional[Path]:
        """Find a decision file by ID."""
        for date_dir in DBB_DIR.iterdir():
            if date_dir.is_dir():
                dbb_file = date_dir / f"decision-{decision_id}.dbb"
                if dbb_file.exists():
                    return dbb_file
        return None
    
    def load(self, decision_id: str) -> Optional[Dict]:
        """Load a DBB record by ID."""
        path = self._find_decision(decision_id)
        if path:
            with open(path, 'r') as f:
                return json.load(f)
        return None
    
    def list_decisions(self, date: Optional[str] = None) -> List[Dict]:
        """List all decisions, optionally filtered by date."""
        decisions = []
        
        dirs = [DBB_DIR / date] if date else list(DBB_DIR.iterdir())
        
        for date_dir in dirs:
            if date_dir.is_dir():
                for dbb_file in date_dir.glob("decision-*.dbb"):
                    try:
                        with open(dbb_file, 'r') as f:
                            data = json.load(f)
                            decisions.append({
                                "decision_id": data.get("decision_id"),
                                "timestamp": data.get("temporal_anchor", {}).get("iso8601"),
                                "type": data.get("decision_type"),
                                "target": data.get("target"),
                                "signoff": data.get("steward_signoff", False),
                                "file": str(dbb_file)
                            })
                    except Exception:
                        continue
        
        return sorted(decisions, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def _to_dict(self, obj) -> Dict:
        """Convert dataclass to dict."""
        if hasattr(obj, '__dataclass_fields__'):
            result = {}
            for k, v in asdict(obj).items():
                if v is not None:
                    result[k] = v
            return result
        return obj


# Singleton
_generator: Optional[DBBGenerator] = None


def get_generator() -> DBBGenerator:
    """Get or create DBB generator."""
    global _generator
    if _generator is None:
        _generator = DBBGenerator()
    return _generator


def generate_dbb(
    decision_type: str,
    target: str,
    reasoning_trace: List[str],
    **kwargs
) -> str:
    """Convenience function to generate DBB."""
    return get_generator().generate(
        decision_type=decision_type,
        target=target,
        reasoning_trace=reasoning_trace,
        **kwargs
    )
