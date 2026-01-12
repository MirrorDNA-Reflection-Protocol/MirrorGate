#!/usr/bin/env python3
"""
MirrorGate Rule Engine — Forbidden Output Detection

Detects and blocks:
- Hallucinated facts (claims without fact hash)
- First-person authority claims
- Unauthorized memory writes
- Ownership/legal/medical assertions
"""

import re
from typing import Tuple, Optional

# Violation codes
VIOLATION_HALLUCINATED_FACT = "HALLUCINATED_FACT"
VIOLATION_FIRST_PERSON_AUTHORITY = "FIRST_PERSON_AUTHORITY"
VIOLATION_UNAUTHORIZED_MEMORY = "UNAUTHORIZED_MEMORY_WRITE"
VIOLATION_OWNERSHIP_CLAIM = "OWNERSHIP_CLAIM"
VIOLATION_MEDICAL_LEGAL = "MEDICAL_LEGAL_ASSERTION"

# Approval marker for authorized memory writes
APPROVAL_MARKER = "<!-- APPROVED_WRITE -->"

# First-person authority patterns
FIRST_PERSON_PATTERNS = [
    re.compile(r'\bI (?:have )?decided\b', re.I),
    re.compile(r'\bI (?:have )?verified\b', re.I),
    re.compile(r'\bI (?:have )?confirmed\b', re.I),
    re.compile(r'\bI know for certain\b', re.I),
    re.compile(r'\bI (?:have )?determined\b', re.I),
    re.compile(r'\bI am certain\b', re.I),
]

# Hallucination patterns (fabricated facts)
HALLUCINATION_PATTERNS = [
    re.compile(r'\b(Paul|user|client)\s+(confirmed|said|stated|verified|agreed)\b', re.I),
    re.compile(r'\bthe deal was signed\b', re.I),
    re.compile(r'\bstudies prove\b', re.I),
    re.compile(r'\bresearch shows\b', re.I),
    re.compile(r'\bit has been confirmed\b', re.I),
    re.compile(r'\baccording to sources\b', re.I),
]

# Ownership/acquisition claims
OWNERSHIP_PATTERNS = [
    re.compile(r'\b(acquired|purchased|bought|owns)\b.*\b(company|business|shares)\b', re.I),
    re.compile(r'\b(signed|executed)\s+(contract|agreement|deal)\b', re.I),
]

# Medical/legal assertions
MEDICAL_LEGAL_PATTERNS = [
    re.compile(r'\byou should (take|stop taking)\s+\w+\b', re.I),
    re.compile(r'\b(diagnosed with|diagnosis is)\b', re.I),
    re.compile(r'\blegally (obligated|required|bound)\b', re.I),
    re.compile(r'\bthis constitutes (legal|medical) advice\b', re.I),
]

# Advice patterns (less severe, logged but allowed in some contexts)
ADVICE_PATTERNS = [
    re.compile(r'\byou should definitely\b', re.I),
    re.compile(r'\bI recommend\b', re.I),
]


def check_content(content: str, resource_path: str) -> Tuple[str, Optional[str]]:
    """
    Check content for violations.
    
    Args:
        content: The text content to validate
        resource_path: Path to the resource being written
        
    Returns:
        Tuple of (action: "ALLOW"|"BLOCK", violation_code: str|None)
    """
    
    # Check for unauthorized memory writes
    is_memory_file = any(x in resource_path for x in ['memory.json', 'state.json', 'handoff.json'])
    if is_memory_file and APPROVAL_MARKER not in content:
        return "BLOCK", VIOLATION_UNAUTHORIZED_MEMORY
    
    # Check first-person authority
    for pattern in FIRST_PERSON_PATTERNS:
        if pattern.search(content):
            return "BLOCK", VIOLATION_FIRST_PERSON_AUTHORITY
    
    # Check hallucination patterns
    for pattern in HALLUCINATION_PATTERNS:
        if pattern.search(content):
            return "BLOCK", VIOLATION_HALLUCINATED_FACT
    
    # Check ownership claims
    for pattern in OWNERSHIP_PATTERNS:
        if pattern.search(content):
            return "BLOCK", VIOLATION_OWNERSHIP_CLAIM
    
    # Check medical/legal assertions
    for pattern in MEDICAL_LEGAL_PATTERNS:
        if pattern.search(content):
            return "BLOCK", VIOLATION_MEDICAL_LEGAL
    
    # All checks passed
    return "ALLOW", None


def get_violation_description(code: str) -> str:
    """Return human-readable description of violation code."""
    descriptions = {
        VIOLATION_HALLUCINATED_FACT: "Claim of real-world event without verification",
        VIOLATION_FIRST_PERSON_AUTHORITY: "First-person authority claim",
        VIOLATION_UNAUTHORIZED_MEMORY: "Memory write without approval marker",
        VIOLATION_OWNERSHIP_CLAIM: "Ownership or acquisition assertion",
        VIOLATION_MEDICAL_LEGAL: "Medical or legal assertion",
    }
    return descriptions.get(code, "Unknown violation")
