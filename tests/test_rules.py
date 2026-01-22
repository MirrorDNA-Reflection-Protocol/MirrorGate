#!/usr/bin/env python3
"""
Tests for MirrorGate Rule Engine
"""

import pytest
from src.rules import (
    check_content,
    VIOLATION_HALLUCINATED_FACT,
    VIOLATION_FIRST_PERSON_AUTHORITY,
    VIOLATION_UNAUTHORIZED_MEMORY,
    VIOLATION_OWNERSHIP_CLAIM,
    VIOLATION_MEDICAL_LEGAL,
)


class TestFirstPersonAuthority:
    """Tests for first-person authority detection."""
    
    def test_i_decided(self):
        content = "I decided to proceed with the deployment."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_FIRST_PERSON_AUTHORITY
    
    def test_i_verified(self):
        content = "I verified the numbers are correct."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_FIRST_PERSON_AUTHORITY
    
    def test_i_have_verified(self):
        content = "I have verified that the data is correct."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_FIRST_PERSON_AUTHORITY
    
    def test_i_confirmed(self):
        content = "I confirmed the meeting time."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_FIRST_PERSON_AUTHORITY
    
    def test_allowed_first_person(self):
        # "I think" is allowed - it's not authoritative
        content = "I think we should consider this option."
        action, code = check_content(content, "/test/file.md")
        assert action == "ALLOW"
        assert code is None


class TestHallucinatedFacts:
    """Tests for hallucinated fact detection."""
    
    def test_paul_confirmed(self):
        content = "Paul confirmed the deal was signed on January 5th."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_HALLUCINATED_FACT
    
    def test_user_said(self):
        content = "The user said they wanted to cancel the subscription."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_HALLUCINATED_FACT
    
    def test_studies_prove(self):
        content = "Studies prove that this method is 99% effective."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_HALLUCINATED_FACT
    
    def test_neutral_statement(self):
        content = "The user asked about project timeline."
        action, code = check_content(content, "/test/file.md")
        assert action == "ALLOW"
        assert code is None


class TestUnauthorizedMemory:
    """Tests for unauthorized memory write detection."""
    
    def test_memory_without_marker(self):
        content = '{"last_action": "user asked a question"}'
        action, code = check_content(content, "/path/to/memory.json")
        assert action == "BLOCK"
        assert code == VIOLATION_UNAUTHORIZED_MEMORY
    
    def test_memory_with_marker(self):
        content = '<!-- APPROVED_WRITE -->\n{"last_action": "user asked a question"}'
        action, code = check_content(content, "/path/to/memory.json")
        assert action == "ALLOW"
        assert code is None
    
    def test_non_memory_file(self):
        content = '{"data": "some value"}'
        action, code = check_content(content, "/path/to/notes.json")
        assert action == "ALLOW"
        assert code is None


class TestOwnershipClaims:
    """Tests for ownership claim detection."""
    
    def test_acquired_company(self):
        content = "The company acquired a new business unit last week."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_OWNERSHIP_CLAIM
    
    def test_signed_contract(self):
        content = "We have signed contract documents for review."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_OWNERSHIP_CLAIM


class TestMedicalLegal:
    """Tests for medical/legal assertion detection."""
    
    def test_medical_advice(self):
        content = "You should take ibuprofen for the pain."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_MEDICAL_LEGAL
    
    def test_legal_advice(self):
        content = "You are legally obligated to comply."
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == VIOLATION_MEDICAL_LEGAL


class TestCleanWrites:
    """Tests for content that should be allowed."""
    
    def test_neutral_note(self):
        content = "User asked about project timeline."
        action, code = check_content(content, "/test/file.md")
        assert action == "ALLOW"
        assert code is None
    
    def test_question(self):
        content = "What would help you make this decision?"
        action, code = check_content(content, "/test/file.md")
        assert action == "ALLOW"
        assert code is None
    
    def test_factual_statement(self):
        content = "The meeting is scheduled for 3pm."
        action, code = check_content(content, "/test/file.md")
        assert action == "ALLOW"
        assert code is None
    
    def test_empty_content(self):
        content = ""
        action, code = check_content(content, "/test/file.md")
        assert action == "ALLOW"
        assert code is None
