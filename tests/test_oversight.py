"""
Tests for Oversight System
Covers consent manager, rule engine, and tripwires.
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import os

from src.consent_manager import (
    ConsentManager, 
    PermissionScope, 
    PermissionAction, 
    ContextMode,
    EscalationTrigger
)
from src.rule_engine import RuleEngine, RuleType
from src.tripwires import (
    TripwireSystem, 
    ActionRecord, 
    TripwireType, 
    TripwireResponse
)


class TestConsentManager:
    """Test consent manager permission operations."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create a test consent manager with temp DB."""
        db_path = tmp_path / "test_permissions.db"
        return ConsentManager(db_path=db_path)
    
    def test_grant_permission(self, manager):
        """Test granting a permission."""
        perm = manager.grant_permission(
            scope=PermissionScope.FILESYSTEM,
            action=PermissionAction.READ,
            target="/Users/test/*",
            reason="Test permission"
        )
        
        assert perm.id is not None
        assert perm.scope == PermissionScope.FILESYSTEM
        assert perm.action == PermissionAction.READ
        assert perm.target == "/Users/test/*"
    
    def test_check_permission_granted(self, manager):
        """Test checking a granted permission."""
        manager.grant_permission(
            scope=PermissionScope.FILESYSTEM,
            action=PermissionAction.READ,
            target="/Users/test/*"
        )
        
        # Should match
        assert manager.check_permission(
            PermissionScope.FILESYSTEM,
            PermissionAction.READ,
            "/Users/test/file.txt"
        ) is True
    
    def test_check_permission_denied(self, manager):
        """Test checking a non-existent permission."""
        # No permissions granted
        assert manager.check_permission(
            PermissionScope.NETWORK,
            PermissionAction.SEND,
            "api.example.com"
        ) is False
    
    def test_revoke_permission(self, manager):
        """Test revoking a permission."""
        perm = manager.grant_permission(
            scope=PermissionScope.VAULT,
            action=PermissionAction.WRITE,
            target="~/MirrorDNA-Vault/*"
        )
        
        # Revoke
        assert manager.revoke_permission(perm.id) is True
        
        # Should no longer work
        assert manager.check_permission(
            PermissionScope.VAULT,
            PermissionAction.WRITE,
            "~/MirrorDNA-Vault/test.md"
        ) is False
    
    def test_permission_with_expiry(self, manager):
        """Test permission expiry."""
        # Create permission that expires in the past
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        perm = manager.grant_permission(
            scope=PermissionScope.DEVICE,
            action=PermissionAction.EXECUTE,
            target="*",
            expires_at=past
        )
        
        # Should not match (expired)
        assert manager.check_permission(
            PermissionScope.DEVICE,
            PermissionAction.EXECUTE,
            "some_command"
        ) is False
    
    def test_decay_expired(self, manager):
        """Test removal of expired permissions."""
        # Create past permission
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        manager.grant_permission(
            scope=PermissionScope.MESSAGING,
            action=PermissionAction.SEND,
            target="*",
            expires_at=past
        )
        
        # Create future permission
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        manager.grant_permission(
            scope=PermissionScope.FILESYSTEM,
            action=PermissionAction.READ,
            target="*",
            expires_at=future
        )
        
        # Decay should remove 1
        removed = manager.decay_expired()
        assert removed == 1
        
        # Should have 1 remaining
        assert len(manager.list_permissions()) == 1


class TestRuleEngine:
    """Test rule engine evaluation."""
    
    @pytest.fixture
    def engine(self, tmp_path):
        """Create rule engine with temp rules file."""
        rules_path = tmp_path / "test_rules.yaml"
        return RuleEngine(rules_path=rules_path)
    
    def test_default_rules_loaded(self, engine):
        """Test that default rules are loaded."""
        rules = engine.list_rules()
        assert len(rules) >= 3  # Should have defaults
    
    def test_credential_block_rule(self, engine):
        """Test that credential patterns are blocked."""
        triggered = engine.evaluate_rules(
            action="read",
            content="Here is the api_key: abc123",
            context="all"
        )
        
        blockers = [r for r in triggered if r["type"] == "hard_block"]
        assert len(blockers) >= 1
        assert any("credential" in r["message"].lower() for r in blockers)
    
    def test_safe_content_passes(self, engine):
        """Test that safe content doesn't trigger blocks."""
        triggered = engine.evaluate_rules(
            action="write",
            content="This is a normal document about Python programming.",
            context="all"
        )
        
        blockers = [r for r in triggered if r["type"] == "hard_block"]
        assert len(blockers) == 0
    
    def test_frequency_warning(self, engine):
        """Test frequency-based warning."""
        triggered = engine.evaluate_rules(
            action="tool_call",
            content="",
            context="all",
            frequency_context={"action_count": 25}  # Exceeds 20
        )
        
        warnings = [r for r in triggered if r["type"] == "soft_warn"]
        assert len(warnings) >= 1


class TestTripwireSystem:
    """Test tripwire detection."""
    
    @pytest.fixture
    def tripwires(self, tmp_path):
        """Create tripwire system with temp config."""
        config_path = tmp_path / "test_tripwires.yaml"
        return TripwireSystem(config_path=config_path)
    
    def test_default_configs_loaded(self, tripwires):
        """Test that default tripwire configs are loaded."""
        assert len(tripwires.configs) >= 5
    
    def test_loop_detection(self, tripwires):
        """Test loop detection tripwire."""
        # Record repeated actions
        for i in range(5):
            record = ActionRecord(
                timestamp=datetime.now(timezone.utc),
                action_type="file_write",
                target="/same/file.txt",
                confidence=0.9,
                initiated_by="self",
                success=True
            )
            events = tripwires.record_action(record)
        
        # Should trigger loop detection
        assert any(e.tripwire_type == TripwireType.LOOP_DETECTION for e in events)
    
    def test_confidence_collapse(self, tripwires):
        """Test confidence collapse detection."""
        # Record low-confidence actions
        for i in range(6):
            record = ActionRecord(
                timestamp=datetime.now(timezone.utc),
                action_type=f"action_{i}",
                target=f"/target/{i}",
                confidence=0.3,  # Low confidence
                initiated_by="self",
                success=True
            )
            events = tripwires.record_action(record)
        
        # Should trigger confidence collapse
        assert any(e.tripwire_type == TripwireType.CONFIDENCE_COLLAPSE for e in events)
    
    def test_autonomy_creep(self, tripwires):
        """Test autonomy creep detection."""
        # Record many self-initiated actions
        for i in range(10):
            record = ActionRecord(
                timestamp=datetime.now(timezone.utc),
                action_type=f"action_{i}",
                target=f"/target/{i}",
                confidence=0.9,
                initiated_by="self",  # All self-initiated
                success=True
            )
            events = tripwires.record_action(record)
        
        # Should trigger autonomy creep (100% self-initiated > 40%)
        assert any(e.tripwire_type == TripwireType.AUTONOMY_CREEP for e in events)
    
    def test_normal_behavior_no_triggers(self, tripwires):
        """Test that normal behavior doesn't trigger."""
        # Varied actions, mixed initiation
        actions = [
            ("read", "user"),
            ("write", "user"),
            ("execute", "self"),
            ("read", "user"),
        ]
        
        all_events = []
        for action, initiated_by in actions:
            record = ActionRecord(
                timestamp=datetime.now(timezone.utc),
                action_type=action,
                target="/some/path",
                confidence=0.85,
                initiated_by=initiated_by,
                success=True
            )
            events = tripwires.record_action(record)
            all_events.extend(events)
        
        # Should not trigger anything critical
        assert len(all_events) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
