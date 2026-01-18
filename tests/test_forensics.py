"""
Tests for Session Forensics
Covers session capture, DBB generation, replay, and export.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone

from src.forensics.session_capture import (
    SessionCapture, 
    begin_session, 
    end_session,
    Session
)
from src.forensics.dbb_generator import (
    DBBGenerator,
    generate_dbb,
    SystemState,
    EvidenceNode
)
from src.forensics.replay import SessionReplay, list_sessions
from src.forensics.export import export_session


class TestSessionCapture:
    """Test session capture functionality."""
    
    def test_session_creation(self):
        """Test creating a new session."""
        session = SessionCapture(actor="test_actor", context_mode="work")
        
        assert session.session_id is not None
        assert session.session.actor == "test_actor"
        assert session.session.context_mode == "work"
    
    def test_record_action(self):
        """Test recording an action."""
        session = SessionCapture()
        
        action_id = session.record_action(
            action_type="write",
            target="/test/path.txt",
            content="Test content here",
            result="ALLOW",
            confidence=0.9
        )
        
        assert action_id is not None
        assert len(session.session.actions) == 1
        assert session.session.metrics.total_actions == 1
    
    def test_record_multiple_actions(self):
        """Test recording multiple actions with metrics."""
        session = SessionCapture()
        
        session.record_action("write", "/path1", "content", "ALLOW", 0.9)
        session.record_action("write", "/path2", "content", "BLOCK", 0.5)
        session.record_action("write", "/path3", "content", "REWRITE", 0.7)
        
        assert session.session.metrics.total_actions == 3
        assert session.session.metrics.blocked_actions == 1
        assert session.session.metrics.rewrites == 1
    
    def test_record_decision_point(self):
        """Test recording a decision point."""
        session = SessionCapture()
        action_id = session.record_action("write", "/path", "content", "ALLOW", 0.8)
        
        decision_id = session.record_decision_point(
            action_id=action_id,
            alternatives=["Option A", "Option B"],
            chosen="Option A",
            rationale="Lower risk option",
            confidence=0.75
        )
        
        assert decision_id is not None
        assert len(session.session.decision_points) == 1
    
    def test_snapshot_permissions(self):
        """Test permission snapshots."""
        session = SessionCapture()
        
        session.snapshot_permissions(
            active_permissions=[{"scope": "filesystem", "action": "read"}],
            context_mode="work"
        )
        
        assert len(session.session.permission_snapshots) == 1
    
    def test_session_data_export(self):
        """Test getting session data as dict."""
        session = SessionCapture()
        session.record_action("test", "/path", "content", "ALLOW", 0.8)
        
        data = session.get_session_data()
        
        assert isinstance(data, dict)
        assert "session_id" in data
        assert "actions" in data
        assert len(data["actions"]) == 1


class TestDBBGenerator:
    """Test DBB sidecar generation."""
    
    def test_dbb_generation(self, tmp_path, monkeypatch):
        """Test generating a DBB record."""
        # Use temp directory
        import src.forensics.dbb_generator as dbb_mod
        monkeypatch.setattr(dbb_mod, "DBB_DIR", tmp_path / "dbb")
        
        generator = DBBGenerator()
        
        path = generator.generate(
            decision_type="BLOCK",
            target="/test/path.txt",
            reasoning_trace=["Step 1: Analyze content", "Step 2: Detect violation"],
            confidence=0.9
        )
        
        assert Path(path).exists()
        
        # Verify content
        with open(path, 'r') as f:
            data = json.load(f)
        
        assert data.get("decision_type") == "BLOCK"
        assert data.get("target") == "/test/path.txt"
        assert "@context" in data  # JSON-LD
    
    def test_dbb_with_system_state(self, tmp_path, monkeypatch):
        """Test DBB with system state included."""
        import src.forensics.dbb_generator as dbb_mod
        monkeypatch.setattr(dbb_mod, "DBB_DIR", tmp_path / "dbb")
        
        generator = DBBGenerator()
        
        state = SystemState(
            core_model="claude-3",
            active_context_hash="abc123",
            policy_hash="def456",
            gate_chain_version="1.0",
            rules_version="1.0"
        )
        
        path = generator.generate(
            decision_type="ALLOW",
            target="/path",
            reasoning_trace=["Passed all gates"],
            system_state=state
        )
        
        assert Path(path).exists()
    
    def test_dbb_chain_hash(self, tmp_path, monkeypatch):
        """Test that chain hash is computed."""
        import src.forensics.dbb_generator as dbb_mod
        monkeypatch.setattr(dbb_mod, "DBB_DIR", tmp_path / "dbb")
        
        generator = DBBGenerator()
        path = generator.generate(
            decision_type="BLOCK",
            target="/path",
            reasoning_trace=["Step 1"]
        )
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        assert "chain_hash" in data
        assert len(data["chain_hash"]) == 64  # SHA-256


class TestSessionReplayAndExport:
    """Test session replay and export functionality."""
    
    @pytest.fixture
    def sample_session(self, tmp_path, monkeypatch):
        """Create a sample session for testing."""
        import src.forensics.session_capture as sc_mod
        monkeypatch.setattr(sc_mod, "SESSIONS_DIR", tmp_path / "sessions")
        
        session = SessionCapture(actor="test", context_mode="work")
        session.record_action("write", "/path1", "content1", "ALLOW", 0.9)
        session.record_action("write", "/path2", "content2", "BLOCK", 0.4)
        session.record_action("write", "/path3", "content3", "ALLOW", 0.8)
        
        session.record_decision_point(
            action_id=session.session.actions[1].action_id,
            alternatives=["Allow", "Block"],
            chosen="Block",
            rationale="Content violated rules",
            confidence=0.85
        )
        
        session.end_session()
        
        return session.session_id, tmp_path / "sessions"
    
    def test_session_replay_load(self, sample_session, monkeypatch):
        """Test loading a session for replay."""
        session_id, sessions_dir = sample_session
        
        import src.forensics.replay as replay_mod
        monkeypatch.setattr(replay_mod, "SESSIONS_DIR", sessions_dir)
        
        replay = SessionReplay(session_id)
        
        assert replay.total_actions == 3
        assert len(replay.decision_points) == 1
    
    def test_session_replay_step(self, sample_session, monkeypatch):
        """Test stepping through a session."""
        session_id, sessions_dir = sample_session
        
        import src.forensics.replay as replay_mod
        monkeypatch.setattr(replay_mod, "SESSIONS_DIR", sessions_dir)
        
        replay = SessionReplay(session_id)
        
        state1 = replay.step()
        assert state1 is not None
        assert state1.action_index == 0
        
        state2 = replay.step()
        assert state2.action_index == 1
        assert state2.decision_at_action is not None  # Has decision
    
    def test_session_world_view(self, sample_session, monkeypatch):
        """Test world view reconstruction."""
        session_id, sessions_dir = sample_session
        
        import src.forensics.replay as replay_mod
        monkeypatch.setattr(replay_mod, "SESSIONS_DIR", sessions_dir)
        
        replay = SessionReplay(session_id)
        
        world_view = replay.get_world_view(1)  # At action 1
        
        assert "what_was_known" in world_view
        assert world_view["what_was_known"]["prior_actions"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
