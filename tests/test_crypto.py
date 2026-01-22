#!/usr/bin/env python3
"""
Tests for MirrorGate Crypto Layer
"""

import os
import json
import pytest
import tempfile
from pathlib import Path

# Temporarily override paths for testing
import src.crypto as crypto_module

@pytest.fixture(autouse=True)
def temp_mirrorgate_dir(tmp_path, monkeypatch):
    """Use temporary directory for all crypto operations."""
    test_dir = tmp_path / ".mirrorgate"
    test_dir.mkdir()
    keys_dir = test_dir / "keys"
    keys_dir.mkdir()
    
    monkeypatch.setattr(crypto_module, "MIRRORGATE_DIR", test_dir)
    monkeypatch.setattr(crypto_module, "KEYS_DIR", keys_dir)
    monkeypatch.setattr(crypto_module, "AUDIT_LOG", test_dir / "audit_log.jsonl")
    monkeypatch.setattr(crypto_module, "CHAIN_STATE", test_dir / "chain_state.json")
    
    return test_dir


class TestKeyGeneration:
    """Tests for Ed25519 key generation."""
    
    def test_generate_keypair(self, temp_mirrorgate_dir):
        from src.crypto import generate_keypair, KEYS_DIR
        
        private_key, public_key = generate_keypair()
        
        assert private_key is not None
        assert public_key is not None
        assert (KEYS_DIR / "private.pem").exists()
        assert (KEYS_DIR / "public.pem").exists()
    
    def test_load_private_key(self, temp_mirrorgate_dir):
        from src.crypto import generate_keypair, load_private_key
        
        generate_keypair()
        loaded = load_private_key()
        
        assert loaded is not None
    
    def test_load_generates_if_missing(self, temp_mirrorgate_dir):
        from src.crypto import load_private_key, KEYS_DIR
        
        # Keys don't exist yet
        assert not (KEYS_DIR / "private.pem").exists()
        
        # Load should generate them
        loaded = load_private_key()
        
        assert loaded is not None
        assert (KEYS_DIR / "private.pem").exists()


class TestDecisionRecord:
    """Tests for decision record generation."""
    
    def test_generate_record_block(self, temp_mirrorgate_dir):
        from src.crypto import generate_decision_record
        
        record = generate_decision_record(
            action="BLOCK",
            resource="/test/file.md",
            violation_code="TEST_VIOLATION",
            hash_before="abc123",
            hash_after="def456"
        )
        
        assert record["action"] == "BLOCK"
        assert record["resource"] == "/test/file.md"
        assert record["violation_code"] == "TEST_VIOLATION"
        assert record["hash_before"] == "abc123"
        assert record["hash_after"] == "def456"
        assert "event_id" in record
        assert "timestamp" in record
        assert "chain_hash" in record
        assert "signature" in record
    
    def test_generate_record_allow(self, temp_mirrorgate_dir):
        from src.crypto import generate_decision_record
        
        record = generate_decision_record(
            action="ALLOW",
            resource="/test/file.md",
            violation_code=None,
            hash_before="abc123",
            hash_after="abc456"
        )
        
        assert record["action"] == "ALLOW"
        assert record["violation_code"] is None


class TestHashChaining:
    """Tests for hash chain integrity."""
    
    def test_first_record_uses_genesis(self, temp_mirrorgate_dir):
        from src.crypto import get_previous_hash, generate_decision_record
        
        assert get_previous_hash() == "GENESIS"
        
        generate_decision_record(
            action="ALLOW",
            resource="/test/file.md",
            violation_code=None,
            hash_before="a",
            hash_after="b"
        )
        
        # After first record, prev hash should change
        assert get_previous_hash() != "GENESIS"
    
    def test_chain_continuity(self, temp_mirrorgate_dir):
        from src.crypto import generate_decision_record, get_previous_hash
        
        r1 = generate_decision_record(
            action="ALLOW",
            resource="/test/1.md",
            violation_code=None,
            hash_before="a",
            hash_after="b"
        )
        
        hash_after_r1 = get_previous_hash()
        assert hash_after_r1 == r1["chain_hash"]
        
        r2 = generate_decision_record(
            action="BLOCK",
            resource="/test/2.md",
            violation_code="TEST",
            hash_before="c",
            hash_after="d"
        )
        
        hash_after_r2 = get_previous_hash()
        assert hash_after_r2 == r2["chain_hash"]
        assert hash_after_r2 != hash_after_r1


class TestAuditLog:
    """Tests for audit log operations."""
    
    def test_append_to_audit_log(self, temp_mirrorgate_dir):
        from src.crypto import append_to_audit_log, AUDIT_LOG
        
        record = {"event_id": "test123", "action": "ALLOW"}
        append_to_audit_log(record)
        
        assert AUDIT_LOG.exists()
        content = AUDIT_LOG.read_text()
        assert "test123" in content
    
    def test_verify_chain_empty(self, temp_mirrorgate_dir):
        from src.crypto import verify_chain
        
        is_valid, error = verify_chain()
        assert is_valid is True
        assert error is None
    
    def test_verify_chain_valid(self, temp_mirrorgate_dir):
        from src.crypto import generate_decision_record, append_to_audit_log, verify_chain
        
        for i in range(3):
            record = generate_decision_record(
                action="ALLOW",
                resource=f"/test/{i}.md",
                violation_code=None,
                hash_before=f"a{i}",
                hash_after=f"b{i}"
            )
            append_to_audit_log(record)
        
        is_valid, error = verify_chain()
        assert is_valid is True
        assert error is None


class TestFileHash:
    """Tests for file hashing."""
    
    def test_compute_file_hash(self, tmp_path):
        from src.crypto import compute_file_hash
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        
        hash1 = compute_file_hash(str(test_file))
        hash2 = compute_file_hash(str(test_file))
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
    
    def test_hash_missing_file(self):
        from src.crypto import compute_file_hash
        
        result = compute_file_hash("/nonexistent/file.txt")
        assert result == "FILE_NOT_FOUND"
