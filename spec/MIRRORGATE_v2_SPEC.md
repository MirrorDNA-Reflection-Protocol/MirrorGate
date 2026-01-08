# ⟡ MirrorGate — Wild Runtime Cryptographic Enforcement

**Specification v2.0 (Final)**

**Status:** Production-grade  
**Mode:** Live / Non-Simulated / Defensible  
**Audience:** Systems engineers, auditors, regulators, skeptics  
**Purpose:** Deterministically subordinate probabilistic AI systems to human-owned authority

---

## 0. Design Intent (Read First)

This system is **not** designed to prove:
- AI is safe
- hallucinations are solved
- models are truthful

This system **does prove**:

A probabilistic model can be placed under deterministic, cryptographically auditable control — without prompt tricks, role-play, or deception.

MirrorGate is **governance infrastructure**, not an AI personality.

---

## 1. Operating Principles (Non-Negotiable)

1. **The LLM is not trusted**
2. **The LLM is not authoritative**
3. **The LLM is not the system**
4. **All authority lives outside the model**
5. **Every decision is machine-verifiable**
6. **Human absence does not imply autonomy**

---

## 2. Wild Runtime Definition

A "wild runtime" means:
- No hardcoded demo strings
- No pre-staged hallucinations
- No prompts telling the model what to fail
- No scripted outcomes
- No visual sleight-of-hand

The system reacts only to **actual writes**, **actual outputs**, and **actual violations**.

---

## 3. System Topology

```
User / Agent
     ↓
[ Write Attempt ]
     ↓
MirrorGate (Pre-Write Intercept)
     ↓
LLM / Tool / Agent (Untrusted)
     ↓
MirrorGate (Post-Write Validation)
     ↓
ALLOW → Commit
BLOCK → Revert + Log + Sign
```

MirrorGate **wraps reality**, not inference.

---

## 4. Enforcement Scope

MirrorGate MUST intercept:
- File writes (.md, .txt, .json)
- Memory commits
- Vault updates
- Agent-initiated persistence
- Cross-agent handoffs

MirrorGate MUST NOT:
- Modify prompts
- Steer model reasoning
- Inject personality
- Rewrite outputs unless blocking

---

## 5. Threat Model

MirrorGate defends against:
- Hallucinated facts
- Fabricated causality
- Unauthorized claims
- Memory poisoning
- Silent drift
- Agent persistence without consent

MirrorGate does **not** attempt to:
- Detect intent
- Judge intelligence
- Interpret emotion

---

## 6. Rule Engine (Hard Constraints)

### 6.1 Forbidden Output Classes

Any write containing the following **must be blocked**:
- Claims of real-world events without a matching fact hash
- Ownership, acquisition, legal, or medical assertions
- First-person authority ("I decided", "I verified", "I know")
- Recommendations framed as facts
- Memory writes without explicit approval marker

---

## 7. Cryptographic Accountability Layer

### 7.1 Decision Record

Every ALLOW or BLOCK event MUST generate a record:

```json
{
  "event_id": "uuid-v7",
  "timestamp": "ISO-8601",
  "actor": "agent | user | system",
  "action": "ALLOW | BLOCK",
  "resource": "path/to/file.md",
  "violation_code": "HALLUCINATION | UNVERIFIED_FACT | UNAUTHORIZED_WRITE",
  "hash_before": "sha256",
  "hash_after": "sha256",
  "mirror_gate_version": "2.0"
}
```

### 7.2 Signing

- Each record is signed with a local private key
- Public key stored separately
- Signature appended to immutable log

### 7.3 Hash Chaining

Each record includes the hash of the previous record:

```
H(n) = SHA256(record_n || H(n-1))
```

This creates a **tamper-evident chain**.

---

## 8. Optional ZK Extension (Not Required for v2)

If enabled later:
- MirrorGate can generate a ZK proof that:
  - A rule was applied
  - A block occurred
  - Without revealing content

This is **explicitly out of scope** for v2 and must not be implemented now.

---

## 9. Visual Runtime Requirements (For Recording)

The following must be visible **without narration**:
- Terminal running MirrorGate daemon
- Clear `[BLOCK]` / `[ALLOW]` outputs
- Timestamped logs
- No human interaction during enforcement

The human may **leave the frame**.
The system must continue operating deterministically.

---

## 10. What This Is Not

MirrorGate is not:
- A safety promise
- A compliance guarantee
- A truth oracle
- A moral agent
- A censorship layer

It is a **control plane**.

---

## 11. What Can Be Defended Publicly

You can truthfully say:
- "We do not trust the model."
- "The model cannot persist memory without consent."
- "All writes are audited and signed."
- "The system behaves identically with or without a human present."
- "This is infrastructure, not alignment."

You do **not** need to claim:
- Reduced hallucination rates
- Smarter AI
- Ethical superiority

---

## 12. Closure Rule

Once implemented:
- No further features
- No UX polish
- No narrative framing
- No expansion

Run it once.
Verify logs.
Then decide **later** whether it is shown or kept private.

---

## 13. Final Constraint

If at any point this system:
- feels theatrical
- requires explanation
- needs justification
- depends on belief

**Stop. Something is wrong.**

MirrorGate should be boring, cold, and obvious.
That is the point.

---

⟡ End of Specification
