# ⟡ MirrorGate

**Sovereign Inference Control Plane**

> ⧉ Governance before generation.

[![MirrorDNA](https://img.shields.io/badge/MirrorDNA-Protocol-purple)](https://github.com/MirrorDNA-Reflection-Protocol)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17787619.svg)](https://doi.org/10.5281/zenodo.17787619)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)

Policy-driven proxy that governs AI requests **before** they execute. Safety by design, not by hope.

---

## What This Is NOT

- ❌ **Not prompt engineering** — This is infrastructure-level control
- ❌ **Not content moderation** — This is pre-inference policy enforcement
- ❌ **Not an AI wrapper** — This is a cryptographically auditable control plane
- ❌ **Not optional safety** — Fail-closed by default, no bypass

---

## What This IS

Governance control plane for reflective AI inference.

MirrorGate enforces safety, policy, and cryptographic accountability around AI inference. It treats the LLM as an untrusted CPU — performing computation only — while all authority, memory, and identity live outside the model.

## Quick Start

```bash
# Install dependencies
npm install

# Generate signing keys
npm run keygen

# Start development server
npm run dev

# Build for production
npm run build
npm start
```

## Architecture

```
User Request
     ↓
┌─────────────────────────────┐
│        GATE CHAIN           │
│ G0: Transport & Auth        │
│ G1: Hard Refusal            │
│ G2: Domain Risk             │
│ G3: Injection Detection     │
│ G4: Size & Complexity       │
│ G5: Intent Classification   │
└─────────────────────────────┘
     ↓
┌─────────────────────────────┐
│    LLM INFERENCE            │
│    (Untrusted)              │
└─────────────────────────────┘
     ↓
┌─────────────────────────────┐
│      FILTER CHAIN           │
│ F1: Prescriptive Language   │
│ F2: Uncertainty Markers     │
│ F3: Identity Claims         │
│ F4: Schema Compliance       │
└─────────────────────────────┘
     ↓
┌─────────────────────────────┐
│    CRYPTO AUDIT             │
│    Ed25519 Signing          │
│    SHA256 Hash Chain        │
└─────────────────────────────┘
     ↓
Response
```

## API

### POST /api/reflect

Main inference endpoint.

**Request:**
```json
{
  "session_id": "uuid",
  "request_id": "uuid",
  "input": "your prompt",
  "profile": "default",
  "consent": {
    "save_to_vault": false,
    "log_opt_in": true
  }
}
```

**Response:**
```json
{
  "output": "response text",
  "safety_outcome": "allowed|rewritten|refused",
  "model_used": "claude-3-opus",
  "signature": "base64-sig",
  "audit_hash": "sha256"
}
```

### GET /api/health

Health check endpoint.

## Configuration

Create `mirrorgate.yaml` or `~/.mirrorgate/config.yaml`:

```yaml
server:
  port: 8088
  host: "127.0.0.1"

auth:
  api_keys:
    - "your-api-key"
  allowed_origins:
    - "https://activemirror.ai"

inference:
  backends:
    - name: claude
      type: anthropic
      model: claude-3-opus-20240229
  default: claude
```

## Policy Profiles

Policies define allowed behavior. See `policies/` directory.

```yaml
name: default
postfilters:
  - prescriptive
  - uncertainty
  - identity
domains:
  medical: reflective
  legal: reflective
```

## Cryptographic Audit

Every request generates a signed, hash-chained audit record:

```json
{
  "event_id": "uuid-v7",
  "action": "ALLOW",
  "hash_input": "sha256",
  "hash_output": "sha256",
  "prev_record_hash": "sha256",
  "signature": "ed25519"
}
```

Verify the audit chain:
```bash
# Coming soon: verification CLI
```

## Core Principles

1. **The LLM is not trusted** — It performs computation only
2. **The LLM is not authoritative** — All authority lives outside
3. **Fail-closed** — Any error returns safe refusal
4. **Cryptographically auditable** — Every decision is signed

---

## MirrorDNA Ecosystem

MirrorGate is part of the **MirrorDNA** ecosystem for sovereign AI:

| Component | Description | Link |
|-----------|-------------|------|
| **MirrorDNA Standard** | Constitutional anchor for reflective AI | [GitHub](https://github.com/MirrorDNA-Reflection-Protocol/MirrorDNA-Standard) |
| **SCD Protocol** | Deterministic state management | [GitHub](https://github.com/MirrorDNA-Reflection-Protocol/SCD-Protocol) |
| **MirrorBrain** | Local-first orchestration runtime | [GitHub](https://github.com/MirrorDNA-Reflection-Protocol/MirrorBrain) |
| **Active Mirror Identity** | Portable AI identity (Mirror Seed) | [GitHub](https://github.com/MirrorDNA-Reflection-Protocol/active-mirror-identity) |
| **MirrorGate** | Inference control plane (you are here) | — |
| **Glyph Engine** | Cryptographic attestation | [GitHub](https://github.com/MirrorDNA-Reflection-Protocol/glyph-engine) |

---

**⟡ Built by [MirrorDNA](https://github.com/MirrorDNA-Reflection-Protocol)**
*Infrastructure, not alignment. Governance before generation.*
