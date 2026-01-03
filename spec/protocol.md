# MirrorGate Specification (v1.0)

**Component:** MirrorGate  
**Part of:** MirrorDNA Standard · Active MirrorOS  
**Status:** Draft · Governance First · Model Agnostic  

---

## 📌 Overview

**MirrorGate** is the sovereign inference control plane for Reflective AI. It acts as a policy-driven proxy that enforces MirrorDNA governance, ensuring AI models function as *reflection engines* only.

It sits between client interfaces and inference backends, providing:
- Deterministic safety outcomes.
- Model-agnostic policy enforcement.
- Immutable audit trails.
- Fail-closed security architecture.

---

## 🧱 Section 1 — Protocol Definitions

### 1.1 Inference API
**Endpoint:** `POST /api/reflect`  
**Transport:** JSON over TLS  
**Auth:** Scoped API key or HMAC signature.

### 1.2 Request Envelope
```json
{
  "session_id": "string",
  "request_id": "string",
  "timestamp": "ISO8601",
  "mode": "local | cloud",
  "profile": "string",
  "intent": "string",
  "input": "string",
  "consent": {
    "save_to_vault": "boolean",
    "log_opt_in": "boolean"
  }
}
```

### 1.3 Response Envelope
```json
{
  "request_id": "string",
  "session_id": "string",
  "output": "string",
  "safety_outcome": "allowed | rewritten | refused",
  "model_used": "string",
  "rule_version": "string",
  "policy_profile": "string",
  "stats": { "processing_time_ms": "number" }
}
```

---

## 🕹 Section 2 — Policy Profiles

### 2.1 Profile Contract
Profiles are data-driven (YAML) and define the execution flow:
```yaml
profile: DEFAULT
prefilters:
  - classify_intent
  - high_risk_guard
postfilters:
  - enforce_reflective_schema
  - forbid_prescriptive_language
  - enforce_uncertainty
```

---

## 📘 Section 3 — Safety Filters

### 3.1 Prefilters
- **classify_intent**: Identifies sensitive domains (medical, legal, financial, etc.).
- **high_risk_guard**: Rejects free-form advice.

### 3.2 Postfilters
- **forbid_prescriptive_language**: Blocks authoritative "you should" patterns.
- **enforce_uncertainty**: Ensures output contains markers of epistemic humility.
- **enforce_reflective_schema**: Validates glyph tokens (⟡, ⧈, ⧉) and reflection semantics.

---

## 🔐 Section 4 — Security & Trust

### 4.1 Authentication
- Scoped API keys restricted by origin.
- HMAC signatures for non-browser clients (IoT/Local).

### 4.2 Fail-Closed Semantics
If any failure occurs (auth, filter, model error), the proxy MUST respond with a generic refusal. No partial or raw model output leaks.

---

## 📊 Section 5 — Audit & Metrics
- Every decision produces an append-only, privacy-safe audit record.
- Metrics track high-risk triggers and policy usage without identifying users (unless consented).
