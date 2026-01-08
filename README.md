# ⟡ MirrorGate — Cryptographic Enforcement Layer

**Version:** 2.1  
**Status:** Production-ready

MirrorGate is a deterministic control plane for AI systems. It gates all writes through validation before allowing persistence — provably.

## What It Proves

**Defensible, verifiable claims:**

| Claim | How It's Proven |
|-------|-----------------|
| Agent cannot persist without validation passing | Staging gateway: writes go to temp, validated, then atomic move |
| Every decision is logged | Append-only audit log with every ALLOW/BLOCK |
| Decisions are tamper-evident | SHA-256 hash chain, Ed25519 signatures |
| Behavior is deterministic | Same input → same output, always |
| Works without human present | System operates identically ± human |

## What It Does NOT Claim

**Honest limitations:**

- ❌ Does NOT catch all hallucinations (only explicit patterns)
- ❌ Does NOT understand meaning (pattern matching, not semantics)
- ❌ Is NOT a safety promise (it's infrastructure)
- ❌ Does NOT make AI truthful (it gates writes)

## Quick Start

```bash
./scripts/run_demo.sh
```

## Gateway Write (Provable)

```python
from src.gateway import gateway_write

# This CANNOT persist without passing validation
success, message = gateway_write(
    content="User asked about timeline.",
    target_path="/path/to/file.md"
)
```

## CLI

```bash
# Write through gateway (validates before persisting)
python -m src.cli write "Clean content" /path/to/file.md

# Validate file without writing
python -m src.cli validate /path/to/file.md
```

## Test

```bash
python3 -m pytest tests/ -v
# 49 tests pass
```

## Audit Log

```bash
cat ~/.mirrorgate/audit_log.jsonl | jq .
```

Each record contains: `event_id`, `timestamp`, `action`, `violation_code`, `chain_hash`, `signature`

## Specification

See [spec/MIRRORGATE_v2_SPEC.md](spec/MIRRORGATE_v2_SPEC.md)

---

⟡ MirrorDNA Project
