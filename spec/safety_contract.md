# MirrorGate Safety Contract

**Version:** 1.0.0  
**Status:** Canonical  

This document defines the deterministic safety outcomes and enforcement requirements for any MirrorGate-compliant implementation.

---

## 🔒 1. Deterministic Outcomes

Every inference request handled by MirrorGate MUST result in exactly one of the following outcomes:

| Outcome | Description | HTTP Status |
| :--- | :--- | :--- |
| **ALLOWED** | The input and output passed all policy filters. | 200 |
| **REWRITTEN** | The input or output was modified by a filter to ensure compliance. | 200 |
| **REFUSED** | A filter blocked the request/response. | 403 |
| **ERROR** | A system failure occurred. | 500 |

---

## 🛡 2. Fail-Closed Semantics

MirrorGate operates on a **Fail-Closed** basis. If the system cannot prove a response is safe, it MUST block it.

A refusal is MANDATORY if any of the following triggers occur:
1. **Authentication Failure**: Missing, invalid, or expired API keys/signatures.
2. **CORS Violation**: Request originating from an unauthorized domain.
3. **Filter Runtime Error**: Any error occurring during the execution of a prefilter or postfilter.
4. **Policy Mismatch**: Inference output fails to meet the structural requirements of the active profile (e.g., missing glyphs).
5. **Backend Error**: Timeout or error from the underlying LLM provider.

---

## ⟡ 3. Reflection Requirements (MirrorDNA Standard)

To be marked as `ALLOWED` or `REWRITTEN`, an output must:
- **Avoid Prescriptive Language**: No "you should" or "must" statements.
- **Maintain Epistemic Humility**: Inclusion of uncertainty markers (e.g., "it is possible that...").
- **Signature Tokens**: Presence of at least one MirrorDNA Glyph (⟡, ⧈, ⧉).

---

## 📊 4. Auditing

Compliance requires that every **REFUSED** outcome logs the specific filter and rule ID that triggered the refusal. This audit record is immutable and stored in the user's MirrorDNA Vault.
