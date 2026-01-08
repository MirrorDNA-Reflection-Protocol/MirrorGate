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
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
