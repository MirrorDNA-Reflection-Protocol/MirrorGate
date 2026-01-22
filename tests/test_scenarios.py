#!/usr/bin/env python3
"""
MirrorGate Demo Scenario Tests

These are the 5 scenarios from the handoff spec,
runnable as tests.
"""

import pytest
from src.rules import check_content


class TestDemoScenarios:
    """Demo scenarios from HO-20260108-MIRRORGATE.md"""
    
    def test_scenario_1_hallucinated_fact_block(self):
        """
        Scenario 1: Hallucinated Fact Block
        Agent writes: "Paul confirmed the deal was signed on January 5th."
        Expected: [BLOCK] — claim of real-world event without fact hash
        """
        content = "Paul confirmed the deal was signed on January 5th."
        action, code = check_content(content, "/test/note.md")
        
        assert action == "BLOCK", f"Expected BLOCK, got {action}"
        assert code == "HALLUCINATED_FACT", f"Expected HALLUCINATED_FACT, got {code}"
    
    def test_scenario_2_unauthorized_memory_write(self):
        """
        Scenario 2: Unauthorized Memory Write
        Agent attempts to write to memory.json without approval marker
        Expected: [BLOCK] — memory write without consent
        """
        content = '{"last_action": "user asked about project"}'
        action, code = check_content(content, "~/.mirrordna/memory.json")
        
        assert action == "BLOCK", f"Expected BLOCK, got {action}"
        assert code == "UNAUTHORIZED_MEMORY_WRITE", f"Expected UNAUTHORIZED_MEMORY_WRITE, got {code}"
    
    def test_scenario_3_clean_write_allowed(self):
        """
        Scenario 3: Clean Write Allowed
        Agent writes a neutral note: "User asked about project timeline."
        Expected: [ALLOW] — no violations
        """
        content = "User asked about project timeline."
        action, code = check_content(content, "/test/note.md")
        
        assert action == "ALLOW", f"Expected ALLOW, got {action}"
        assert code is None, f"Expected no violation code, got {code}"
    
    def test_scenario_4_first_person_authority_block(self):
        """
        Scenario 4: First-Person Authority Block
        Agent writes: "I verified the numbers are correct."
        Expected: [BLOCK] — first-person authority claim
        """
        content = "I verified the numbers are correct."
        action, code = check_content(content, "/test/note.md")
        
        assert action == "BLOCK", f"Expected BLOCK, got {action}"
        assert code == "FIRST_PERSON_AUTHORITY", f"Expected FIRST_PERSON_AUTHORITY, got {code}"
    
    def test_scenario_5_human_absence_deterministic(self):
        """
        Scenario 5: Human Absence Test
        System should behave identically regardless of human presence.
        This test verifies that rule evaluation is deterministic.
        """
        test_cases = [
            ("Paul confirmed the deal.", "BLOCK", "HALLUCINATED_FACT"),
            ("User asked a question.", "ALLOW", None),
            ("I decided to proceed.", "BLOCK", "FIRST_PERSON_AUTHORITY"),
        ]
        
        # Run each case twice - results must be identical
        for content, expected_action, expected_code in test_cases:
            action1, code1 = check_content(content, "/test/note.md")
            action2, code2 = check_content(content, "/test/note.md")
            
            assert action1 == action2, "Rule evaluation must be deterministic"
            assert code1 == code2, "Violation code must be deterministic"
            assert action1 == expected_action
            assert code1 == expected_code


class TestEdgeCases:
    """Edge cases for demo robustness."""
    
    def test_empty_content(self):
        action, code = check_content("", "/test/empty.md")
        assert action == "ALLOW"
    
    def test_whitespace_only(self):
        action, code = check_content("   \n\t  ", "/test/whitespace.md")
        assert action == "ALLOW"
    
    def test_case_insensitivity(self):
        """Patterns should match regardless of case."""
        content = "i VERIFIED the data"
        action, code = check_content(content, "/test/file.md")
        assert action == "BLOCK"
        assert code == "FIRST_PERSON_AUTHORITY"
    
    def test_approved_memory_write(self):
        """Memory write with approval marker should pass."""
        content = "<!-- APPROVED_WRITE -->\n{\"data\": \"value\"}"
        action, code = check_content(content, "/path/to/memory.json")
        assert action == "ALLOW"
