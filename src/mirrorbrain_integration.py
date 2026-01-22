#!/usr/bin/env python3
"""
⟡ MirrorGate ↔ MirrorBrain Integration

Connects MirrorGate enforcement to MirrorBrain's write operations.
All vault writes through MirrorBrain pass through MirrorGate validation.
"""

import json
import requests
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timezone

# MirrorGate imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.gateway import gateway_write
from src.crypto import verify_chain, get_previous_hash
from src.output import log_info, log_error

MIRRORGATE_DIR = Path.home() / ".mirrorgate"
MIRRORBRAIN_STATE = Path.home() / ".mirrordna" / "current_state.json"


def mirrorgate_write(content: str, target_path: str, actor: str = "mirrorbrain") -> Tuple[bool, str]:
    """
    Write content through MirrorGate validation.
    
    This is the main integration point. MirrorBrain calls this instead of
    direct file writes for protected paths.
    
    Args:
        content: Content to write
        target_path: Destination path
        actor: Who initiated the write (for audit)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    return gateway_write(content, target_path)


def check_chain_integrity() -> Dict[str, Any]:
    """
    Verify MirrorGate audit chain integrity.
    
    Returns status for MirrorBrain health checks.
    """
    is_valid, error = verify_chain()
    
    audit_log = MIRRORGATE_DIR / "audit_log.jsonl"
    record_count = 0
    if audit_log.exists():
        with open(audit_log) as f:
            record_count = sum(1 for _ in f)
    
    return {
        "chain_valid": is_valid,
        "error": error,
        "record_count": record_count,
        "last_hash": get_previous_hash(),
        "checked_at": datetime.now(timezone.utc).isoformat()
    }


def get_enforcement_status() -> Dict[str, Any]:
    """
    Get current MirrorGate enforcement status.
    
    For MirrorBrain state daemon integration.
    """
    audit_log = MIRRORGATE_DIR / "audit_log.jsonl"
    
    # Count recent blocks/allows
    blocks = 0
    allows = 0
    last_event = None
    
    if audit_log.exists():
        with open(audit_log) as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get("action") == "BLOCK":
                        blocks += 1
                    else:
                        allows += 1
                    last_event = record
                except:
                    pass
    
    return {
        "status": "active",
        "total_blocks": blocks,
        "total_allows": allows,
        "last_event": last_event.get("timestamp") if last_event else None,
        "last_action": last_event.get("action") if last_event else None,
        "version": "2.1"
    }


def register_with_mirrorbrain():
    """
    Register MirrorGate status with MirrorBrain state.
    
    Called by MirrorBrain state daemon to include MirrorGate in system state.
    """
    status = get_enforcement_status()
    chain = check_chain_integrity()
    
    mirrorgate_state = {
        "mirrorgate": {
            **status,
            "chain_valid": chain["chain_valid"],
            "chain_records": chain["record_count"]
        }
    }
    
    # Write to MirrorBrain integration file
    integration_file = MIRRORGATE_DIR / "mirrorbrain_status.json"
    integration_file.write_text(json.dumps(mirrorgate_state, indent=2))
    
    return mirrorgate_state


# MCP Tool Integration
def mcp_tool_write_validated(content: str, path: str) -> Dict[str, Any]:
    """
    MCP-compatible write function with MirrorGate validation.
    
    Use this as the write handler in MirrorBrain MCP server.
    
    Args:
        content: Content to write
        path: Target path
        
    Returns:
        MCP-compatible response dict
    """
    success, message = mirrorgate_write(content, path)
    
    return {
        "success": success,
        "message": message,
        "validated_by": "mirrorgate",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    # Test integration
    print("⟡ MirrorGate ↔ MirrorBrain Integration Test")
    print("=" * 50)
    
    # Check chain
    chain = check_chain_integrity()
    print(f"Chain valid: {chain['chain_valid']}")
    print(f"Records: {chain['record_count']}")
    
    # Get status
    status = get_enforcement_status()
    print(f"Status: {status['status']}")
    print(f"Blocks: {status['total_blocks']}")
    print(f"Allows: {status['total_allows']}")
    
    # Register
    print("\nRegistering with MirrorBrain...")
    state = register_with_mirrorbrain()
    print(json.dumps(state, indent=2))
