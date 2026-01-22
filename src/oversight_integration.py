"""
Oversight Integration — Connects Oversight layers with MirrorGate

Called at:
- Gate entry: check_permission()
- Gate exit: evaluate_rules(), check_tripwires()
- Action complete: log_to_audit(), update_metrics()
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .consent_manager import ConsentManager, PermissionScope, PermissionAction, ContextMode
from .rule_engine import RuleEngine
from .tripwires import TripwireSystem, ActionRecord, TripwireEvent


class OversightIntegration:
    """
    Central integration point for all Oversight layers.
    Provides a unified interface for MirrorGate.
    """
    
    def __init__(self):
        self.consent_manager = ConsentManager()
        self.rule_engine = RuleEngine()
        self.tripwires = TripwireSystem()
        
        # Session context
        self.current_context: ContextMode = ContextMode.NULL
        self.action_count: int = 0
        self.session_start: datetime = datetime.now(timezone.utc)
    
    def set_context(self, mode: str):
        """Set the current context mode."""
        try:
            self.current_context = ContextMode(mode)
        except ValueError:
            self.current_context = ContextMode.NULL
    
    def check_permission(
        self,
        scope: str,
        action: str,
        target: str
    ) -> Dict[str, Any]:
        """
        Check if an action is permitted.
        Called at gate entry.
        
        Returns:
            {
                "allowed": bool,
                "reason": str,
                "escalation_required": bool
            }
        """
        try:
            scope_enum = PermissionScope(scope)
            action_enum = PermissionAction(action)
        except ValueError:
            return {
                "allowed": False,
                "reason": f"Invalid scope or action: {scope}/{action}",
                "escalation_required": False
            }
        
        # Check consent
        has_permission = self.consent_manager.check_permission(
            scope_enum,
            action_enum,
            target,
            self.current_context
        )
        
        if not has_permission:
            return {
                "allowed": False,
                "reason": f"No permission for {scope}/{action} on {target}",
                "escalation_required": True
            }
        
        return {
            "allowed": True,
            "reason": "Permission granted",
            "escalation_required": False
        }
    
    def evaluate_action(
        self,
        action: str,
        content: str,
        initiated_by: str = "user"
    ) -> Dict[str, Any]:
        """
        Evaluate an action against rules and tripwires.
        Called at gate exit.
        
        Returns:
            {
                "allowed": bool,
                "blocked_by_rules": List[dict],
                "warnings": List[dict],
                "tripwires_triggered": List[TripwireEvent]
            }
        """
        self.action_count += 1
        
        # Evaluate rules
        triggered_rules = self.rule_engine.evaluate_rules(
            action=action,
            content=content,
            context=self.current_context.value,
            frequency_context={"action_count": self.action_count}
        )
        
        # Separate blocking rules from warnings
        blockers = [r for r in triggered_rules if r["type"] == "hard_block"]
        warnings = [r for r in triggered_rules if r["type"] in ["soft_warn", "log_only"]]
        
        # Record action for tripwire analysis
        action_record = ActionRecord(
            timestamp=datetime.now(timezone.utc),
            action_type=action,
            target=content[:100] if content else "",  # Truncate for storage
            confidence=0.8,  # TODO: Get actual confidence from gate chain
            initiated_by=initiated_by,
            success=len(blockers) == 0,
            metadata={}
        )
        
        tripwire_events = self.tripwires.record_action(action_record)
        
        return {
            "allowed": len(blockers) == 0,
            "blocked_by_rules": blockers,
            "warnings": warnings,
            "tripwires_triggered": tripwire_events
        }
    
    def on_action_complete(
        self,
        action: str,
        target: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Called after an action completes.
        Updates metrics and saves state.
        """
        # Could log to audit here
        # Could update frequency counters
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current oversight status summary."""
        return {
            "context": self.current_context.value,
            "session_start": self.session_start.isoformat(),
            "action_count": self.action_count,
            "permissions_active": len(self.consent_manager.list_permissions()),
            "rules_loaded": len(self.rule_engine.list_rules()),
            "tripwire_configs": len(self.tripwires.configs)
        }
    
    def end_session(self):
        """Clean up at end of session."""
        # Decay expired permissions
        self.consent_manager.decay_expired()
        
        # Save tripwire baseline
        self.tripwires.save_baseline()


# Singleton instance for easy import
_oversight: Optional[OversightIntegration] = None


def get_oversight() -> OversightIntegration:
    """Get or create the oversight integration singleton."""
    global _oversight
    if _oversight is None:
        _oversight = OversightIntegration()
    return _oversight
