# ⟡ MirrorGate — Cryptographic Enforcement Layer

**Version:** 2.0  
**Status:** Production-ready

MirrorGate is a deterministic control plane for AI systems. It intercepts file writes, validates against rules, and creates tamper-evident audit logs — all without trusting the model.

## What It Does

- **Watches** configured paths for file changes
- **Intercepts** writes before they persist
- **Validates** content against forbidden patterns
- **Blocks** hallucinated facts, unauthorized claims, memory writes without consent
- **Signs** every decision with Ed25519
- **Chains** records with SHA-256 for tamper-evidence

## Quick Start

```bash
./scripts/run_demo.sh
```

This:
1. Creates a Python virtual environment
2. Installs dependencies
3. Starts the daemon watching `~/.mirrordna/` and `~/MirrorDNA-Vault/`

## Test

```bash
python3 -m pytest tests/ -v
```

## Try It

With the daemon running:

```bash
# Trigger a BLOCK (hallucinated fact)
echo "Paul confirmed the deal was signed on January 5th." > ~/.mirrordna/test.md

# Trigger an ALLOW (clean write)  
echo "User asked about project timeline." > ~/.mirrordna/clean.md
```

## Audit Log

View the signed audit log:

```bash
cat ~/.mirrorgate/audit_log.jsonl | jq .
```

Each record contains:
- `event_id` — UUID-v7 identifier
- `timestamp` — ISO-8601 UTC
- `action` — ALLOW or BLOCK
- `violation_code` — Why it was blocked (if applicable)
- `chain_hash` — SHA-256 hash including previous record
- `signature` — Ed25519 signature

## What This Is Not

MirrorGate is **not**:
- A safety promise
- A truth oracle
- An AI personality
- A censorship layer

It is **infrastructure** — boring, cold, obvious.

## Specification

See [spec/MIRRORGATE_v2_SPEC.md](spec/MIRRORGATE_v2_SPEC.md) for the full technical specification.

---

⟡ MirrorDNA Project
