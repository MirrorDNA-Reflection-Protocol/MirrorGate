# ⟡ MirrorGate

**Cryptographic Enforcement Layer for AI Systems**

Version 2.1 | Production-ready | 49 tests passing

---

## What It Does

MirrorGate intercepts AI writes **before they persist** and validates them against deterministic rules. Every decision is cryptographically signed and hash-chained.

**This is provable governance, not prompt engineering.**

---

## Quick Start

```bash
# Run the demo
./scripts/demo_recording.sh

# Or start the daemon manually
python3 -m src.daemon ~/.mirrorgate/watched/
```

---

## What It Proves

| Claim | How |
|-------|-----|
| Agent cannot persist without validation | Staging gateway architecture |
| Every decision is logged | Append-only audit log |
| Decisions are tamper-evident | SHA-256 hash chain |
| Records are signed | Ed25519 signatures |
| Works without human present | Deterministic rules |

---

## What It Blocks

- **Hallucinated facts** — "Paul confirmed..." / "Studies prove..."
- **First-person authority** — "I verified..." / "I decided..."
- **Unauthorized memory writes** — Persistence without approval marker
- **Medical/legal assertions** — "You should stop taking..."
- **Ownership claims** — "The deal was signed..."

---

## Integration

```python
from src.gateway import gateway_write

# Write through MirrorGate validation
success, message = gateway_write(
    content="Agent-generated content",
    target_path="/path/to/file.md"
)

if success:
    print("Write committed")
else:
    print(f"Blocked: {message}")
```

---

## CLI

```bash
# Write through gateway
python -m src.cli write "Content here" /path/to/file.md

# Validate without writing
python -m src.cli validate /path/to/file.md

# Check audit chain integrity
python -m src.cli verify-chain
```

---

## Audit Log

Every decision creates a signed record:

```json
{
  "event_id": "uuid-v7",
  "timestamp": "2026-01-09T14:30:00Z",
  "action": "BLOCK",
  "resource": "/path/to/file.md",
  "violation_code": "HALLUCINATED_FACT",
  "hash_before": "sha256...",
  "hash_after": "sha256...",
  "chain_hash": "sha256...",
  "signature": "base64..."
}
```

View the log:
```bash
cat ~/.mirrorgate/audit_log.jsonl | jq .
```

---

## Tests

```bash
python3 -m pytest tests/ -v
# 49 passed
```

---

## Architecture

```
~/.mirrorgate/
  ├── keys/
  │   ├── private.pem      # Ed25519 signing key
  │   └── public.pem       # Verification key
  ├── staging/             # Temp writes before validation
  ├── audit_log.jsonl      # Tamper-evident decision log
  └── chain_state.json     # Hash chain head
```

---

## Documentation

- [One-Pager](docs/ONE_PAGER.md) — Executive summary
- [Specification](spec/MIRRORGATE_v2_SPEC.md) — Full technical spec
- [Protocol](spec/protocol.md) — Wire protocol details

---

## Honest Limitations

- ❌ Does NOT catch all hallucinations (pattern matching only)
- ❌ Does NOT understand semantics
- ❌ Is NOT a safety guarantee
- ❌ Does NOT make AI truthful

**It gates writes. That's it. That's the point.**

---

## Part of MirrorDNA

MirrorGate is part of the [MirrorDNA](https://activemirror.ai) ecosystem — sovereign AI infrastructure for human-controlled AI systems.

---

## License

MIT

---

⟡ N1 Intelligence
