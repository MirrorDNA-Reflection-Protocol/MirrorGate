#!/usr/bin/env python3
"""
Tests for MirrorGate Staging Gateway
"""

import os
import pytest
import tempfile
from pathlib import Path

from src.gateway import (
    gateway_write, stage_write, validate_and_commit,
    get_staging_path, clear_staging, STAGING_DIR
)
from src.rules import VIOLATION_FIRST_PERSON_AUTHORITY, VIOLATION_HALLUCINATED_FACT


class TestStagingGateway:
    """Tests for the staging gateway approach."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path, monkeypatch):
        """Use temp directory for tests."""
        test_staging = tmp_path / "staging"
        test_staging.mkdir()
        monkeypatch.setattr("src.gateway.STAGING_DIR", test_staging)
        
        # Also patch crypto to use temp dir
        import src.crypto as crypto_module
        test_mirrorgate = tmp_path / ".mirrorgate"
        test_mirrorgate.mkdir()
        keys_dir = test_mirrorgate / "keys"
        keys_dir.mkdir()
        monkeypatch.setattr(crypto_module, "MIRRORGATE_DIR", test_mirrorgate)
        monkeypatch.setattr(crypto_module, "KEYS_DIR", keys_dir)
        monkeypatch.setattr(crypto_module, "AUDIT_LOG", test_mirrorgate / "audit_log.jsonl")
        monkeypatch.setattr(crypto_module, "CHAIN_STATE", test_mirrorgate / "chain_state.json")
        
        self.tmp_path = tmp_path
        yield
    
    def test_clean_write_allowed(self):
        """Clean content should be allowed and committed."""
        target = str(self.tmp_path / "output" / "clean.md")
        content = "User asked about project timeline."
        
        success, message = gateway_write(content, target)
        
        assert success is True
        assert "ALLOWED" in message
        assert os.path.exists(target)
        assert open(target).read() == content
    
    def test_violation_blocked(self):
        """Violation should be blocked, nothing written."""
        target = str(self.tmp_path / "output" / "bad.md")
        content = "I verified the numbers are correct."
        
        success, message = gateway_write(content, target)
        
        assert success is False
        assert "BLOCKED" in message
        assert "FIRST_PERSON_AUTHORITY" in message
        assert not os.path.exists(target)
    
    def test_hallucination_blocked(self):
        """Hallucinated fact should be blocked."""
        target = str(self.tmp_path / "output" / "hallucination.md")
        content = "Paul confirmed the deal was signed on Monday."
        
        success, message = gateway_write(content, target)
        
        assert success is False
        assert "BLOCKED" in message
        assert not os.path.exists(target)
    
    def test_staging_then_validate(self):
        """Test two-step staging flow."""
        target = str(self.tmp_path / "output" / "staged.md")
        content = "This is clean content."
        
        # Stage
        staged, msg, staging_path = stage_write(content, target)
        assert staged is True
        assert os.path.exists(staging_path)
        
        # Validate and commit
        success, message = validate_and_commit(staging_path, target)
        assert success is True
        assert os.path.exists(target)
        assert not os.path.exists(staging_path)  # Moved, not copied
    
    def test_staging_path_unique(self):
        """Different targets should get different staging paths."""
        path1 = get_staging_path("/foo/bar.md")
        path2 = get_staging_path("/baz/qux.md")
        
        assert path1 != path2
    
    def test_atomic_move(self):
        """Commit should be atomic (move, not copy)."""
        target = str(self.tmp_path / "output" / "atomic.md")
        content = "Atomic test content."
        
        staged, _, staging_path = stage_write(content, target)
        assert os.path.exists(staging_path)
        
        validate_and_commit(staging_path, target)
        
        # Staging file should be gone (moved)
        assert not os.path.exists(staging_path)
        # Target should exist
        assert os.path.exists(target)


class TestProvableClaims:
    """Tests that validate our provable claims."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path, monkeypatch):
        test_staging = tmp_path / "staging"
        test_staging.mkdir()
        monkeypatch.setattr("src.gateway.STAGING_DIR", test_staging)
        
        import src.crypto as crypto_module
        test_mirrorgate = tmp_path / ".mirrorgate"
        test_mirrorgate.mkdir()
        keys_dir = test_mirrorgate / "keys"
        keys_dir.mkdir()
        monkeypatch.setattr(crypto_module, "MIRRORGATE_DIR", test_mirrorgate)
        monkeypatch.setattr(crypto_module, "KEYS_DIR", keys_dir)
        monkeypatch.setattr(crypto_module, "AUDIT_LOG", test_mirrorgate / "audit_log.jsonl")
        monkeypatch.setattr(crypto_module, "CHAIN_STATE", test_mirrorgate / "chain_state.json")
        self.audit_log = test_mirrorgate / "audit_log.jsonl"
        self.tmp_path = tmp_path
        yield
    
    def test_claim_cannot_persist_without_validation(self):
        """
        PROVABLE CLAIM: Agent cannot persist to protected paths without validation passing.
        
        This test verifies that blocked content NEVER reaches the target path.
        """
        target = str(self.tmp_path / "protected" / "file.md")
        
        violations = [
            "I decided to proceed.",
            "Paul confirmed the meeting.",
            "I verified the data.",
            "Studies prove this works.",
        ]
        
        for content in violations:
            success, _ = gateway_write(content, target)
            assert success is False, f"Violation should be blocked: {content}"
            assert not os.path.exists(target), f"Target should NOT exist after block: {content}"
    
    def test_claim_every_decision_logged(self):
        """
        PROVABLE CLAIM: Every ALLOW and BLOCK is logged.
        """
        target1 = str(self.tmp_path / "output" / "allowed.md")
        target2 = str(self.tmp_path / "output" / "blocked.md")
        
        gateway_write("Clean content.", target1)  # ALLOW
        gateway_write("I verified this.", target2)  # BLOCK
        
        assert self.audit_log.exists()
        log_content = self.audit_log.read_text()
        
        assert "ALLOW" in log_content
        assert "BLOCK" in log_content
    
    def test_claim_deterministic(self):
        """
        PROVABLE CLAIM: Same input always produces same output.
        """
        target = str(self.tmp_path / "output" / "deterministic.md")
        content = "I verified the data is correct."
        
        results = []
        for _ in range(5):
            success, message = gateway_write(content, target)
            results.append((success, "BLOCKED" in message))
        
        # All results should be identical
        assert all(r == results[0] for r in results)
