# ⟡ MirrorGate

**Governance control plane for reflective AI inference.**

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

Part of the MirrorDNA Standard.

⟡ Infrastructure, not alignment.
