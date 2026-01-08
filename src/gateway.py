#!/usr/bin/env python3
"""
MirrorGate Staging Gateway — Pre-Validation Write Control

Provides a staging directory approach:
1. Writes go to ~/.mirrorgate/staging/
2. Validation runs on staged content
3. ALLOW → atomic move to target
4. BLOCK → delete staging file, log decision

This is provable: Agent cannot persist to protected paths without passing validation.
"""

import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple

from .rules import check_content
from .crypto import generate_decision_record, append_to_audit_log, compute_file_hash
from .output import log_block, log_allow, log_record_signed, log_info, log_error

STAGING_DIR = Path.home() / ".mirrorgate" / "staging"


def ensure_staging_dir():
    """Create staging directory if it doesn't exist."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)


def get_staging_path(target_path: str) -> Path:
    """
    Generate a staging path for a target file.
    
    Args:
        target_path: The intended final path
        
    Returns:
        Path in staging directory
    """
    ensure_staging_dir()
    # Use hash of target path to avoid collisions
    path_hash = hashlib.md5(target_path.encode()).hexdigest()[:8]
    basename = os.path.basename(target_path)
    return STAGING_DIR / f"{path_hash}_{basename}"


def stage_write(content: str, target_path: str) -> Tuple[bool, str, Optional[str]]:
    """
    Stage a write for validation.
    
    This is the main entry point for the staging gateway.
    
    Args:
        content: The content to write
        target_path: The intended final destination
        
    Returns:
        Tuple of (allowed: bool, message: str, staging_path: str|None)
    """
    ensure_staging_dir()
    
    staging_path = get_staging_path(target_path)
    
    # Write to staging
    try:
        staging_path.write_text(content, encoding='utf-8')
    except Exception as e:
        return False, f"Failed to write to staging: {e}", None
    
    return True, "Staged successfully", str(staging_path)


def validate_and_commit(staging_path: str, target_path: str) -> Tuple[bool, str]:
    """
    Validate staged content and commit if allowed.
    
    Args:
        staging_path: Path to staged file
        target_path: Intended final destination
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    staging = Path(staging_path)
    
    if not staging.exists():
        return False, "Staging file not found"
    
    # Read staged content
    try:
        content = staging.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"Failed to read staging file: {e}"
    
    # Compute hashes
    hash_staged = compute_file_hash(staging_path)
    hash_before = compute_file_hash(target_path)  # May be "FILE_NOT_FOUND"
    
    # Validate against rules
    action, violation_code = check_content(content, target_path)
    
    resource_name = os.path.basename(target_path)
    
    if action == "BLOCK":
        # Generate and log decision
        record = generate_decision_record(
            action="BLOCK",
            resource=target_path,
            violation_code=violation_code,
            hash_before=hash_before,
            hash_after=hash_staged,
            actor="agent"
        )
        append_to_audit_log(record)
        
        # Log to terminal
        log_block(resource_name, violation_code)
        log_record_signed(record["event_id"], record["chain_hash"])
        
        # Delete staging file (do not commit)
        staging.unlink(missing_ok=True)
        
        return False, f"BLOCKED: {violation_code}"
    
    else:  # ALLOW
        # Ensure target directory exists
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic move from staging to target
        try:
            shutil.move(str(staging), str(target))
        except Exception as e:
            return False, f"Failed to commit: {e}"
        
        hash_after = compute_file_hash(target_path)
        
        # Generate and log decision
        record = generate_decision_record(
            action="ALLOW",
            resource=target_path,
            violation_code=None,
            hash_before=hash_before,
            hash_after=hash_after,
            actor="agent"
        )
        append_to_audit_log(record)
        
        # Log to terminal
        log_allow(resource_name)
        log_record_signed(record["event_id"], record["chain_hash"])
        
        return True, "ALLOWED: Write committed"


def gateway_write(content: str, target_path: str) -> Tuple[bool, str]:
    """
    Full gateway flow: stage → validate → commit or reject.
    
    This is the single entry point for validated writes.
    
    Args:
        content: Content to write
        target_path: Final destination path
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Stage
    staged, msg, staging_path = stage_write(content, target_path)
    if not staged:
        return False, msg
    
    # Validate and commit
    return validate_and_commit(staging_path, target_path)


def list_pending() -> list:
    """List files currently in staging (not yet validated)."""
    ensure_staging_dir()
    return list(STAGING_DIR.glob("*"))


def clear_staging():
    """Clear all staged files (emergency cleanup)."""
    ensure_staging_dir()
    for f in STAGING_DIR.glob("*"):
        f.unlink(missing_ok=True)
