#!/usr/bin/env python3
"""
MirrorGate CLI — Command line interface for validated writes.

Usage:
    python -m src.cli write <content> <target_path>
    python -m src.cli validate <file_path>
    python -m src.cli pending
    python -m src.cli clear
"""

import sys
import argparse

from .gateway import gateway_write, list_pending, clear_staging
from .rules import check_content
from .output import log_startup, log_info


def cmd_write(args):
    """Write content through the gateway."""
    success, message = gateway_write(args.content, args.target)
    print(message)
    return 0 if success else 1


def cmd_validate(args):
    """Validate a file without writing."""
    try:
        with open(args.path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return 1
    
    action, code = check_content(content, args.path)
    
    if action == "ALLOW":
        print(f"✅ ALLOW — No violations detected")
        return 0
    else:
        print(f"⛔ BLOCK — {code}")
        return 1


def cmd_pending(args):
    """List pending staged files."""
    pending = list_pending()
    if not pending:
        print("No files pending in staging.")
    else:
        print(f"Pending files ({len(pending)}):")
        for p in pending:
            print(f"  {p}")
    return 0


def cmd_clear(args):
    """Clear staging directory."""
    clear_staging()
    print("Staging cleared.")
    return 0

# Pulse Integration
try:
    from .pulse.core import pulse
    from .pulse.types import PulseScope
    from .pulse.audit import log_pulse_event
except ImportError:
    pulse = None


def cmd_pulse(args: argparse.Namespace):
    """Handle pulse commands."""
    if not pulse:
        print("Error: Pulse module not available.")
        return 1

    if args.pulse_command == "issue":
        # Parse scopes
        try:
            scopes = [PulseScope(s) for s in args.scopes.split(",")]
        except ValueError as e:
            print(f"Error: Invalid scope. Allowed: {[s.value for s in PulseScope]}")
            return 1
            
        token = pulse.issue_token(
            issued_to=args.device_id,
            scopes=scopes,
            duration_seconds=args.duration
        )
        
        # Log issuance
        log_pulse_event("token_issue", {
            "token_id": token.token_id,
            "issued_to": token.issued_to,
            "scopes": [s.value for s in token.scope]
        })
        
        print(f"Token Issued: {token.token_id}")
        print(f"Signature: {token.signature}")
        print(f"Expires: {token.end.isoformat()}")
        
        # For programmatic use, maybe output JSON?
        import json
        with open(f"{token.token_id}.token.json", "w") as f:
             f.write(token.model_dump_json(indent=2))
        print(f"Token saved to {token.token_id}.token.json")
        return 0
        
    elif args.pulse_command == "verify":
        try:
            import json
            from .pulse.types import PulseToken
            with open(args.token_file, 'r') as f:
                data = json.load(f)
                token = PulseToken(**data)
            
            is_valid = pulse.verify_token(token)
            if is_valid:
                print("✅ Token is VALID")
                return 0
            else:
                print("❌ Token is INVALID or EXPIRED")
                return 1
        except Exception as e:
            print(f"Error verifying token: {e}")
            return 1
            
    else:
        print("Unknown pulse command")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="MirrorGate — Cryptographic Write Enforcement"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # write
    write_parser = subparsers.add_parser("write", help="Write through gateway")
    write_parser.add_argument("content", help="Content to write")
    write_parser.add_argument("target", help="Target file path")
    write_parser.set_defaults(func=cmd_write)
    
    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate file")
    validate_parser.add_argument("path", help="File to validate")
    validate_parser.set_defaults(func=cmd_validate)
    
    # pending
    pending_parser = subparsers.add_parser("pending", help="List pending staged files")
    pending_parser.set_defaults(func=cmd_pending)
    
    # clear
    clear_parser = subparsers.add_parser("clear", help="Clear staging")
    clear_parser.set_defaults(func=cmd_clear)
    
    # pulse
    pulse_parser = subparsers.add_parser("pulse", help="Pulse Token Management")
    pulse_subparsers = pulse_parser.add_subparsers(dest="pulse_command", required=True)
    
    # pulse issue
    issue_parser = pulse_subparsers.add_parser("issue", help="Issue a delegation token")
    issue_parser.add_argument("device_id", help="Device ID (e.g. pixel_01)")
    issue_parser.add_argument("scopes", help="Comma-separated scopes")
    issue_parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    pulse_parser.set_defaults(func=cmd_pulse)
    
    # pulse verify
    verify_parser = pulse_subparsers.add_parser("verify", help="Verify a token file")
    verify_parser.add_argument("token_file", help="Path to token JSON file")
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
