# Mirrorgate Hypervisor — Risk, Legal & Security Assessment

Version: 1.0
Date: 2026-01-27
Scope: All Hypervisor layers (L0–L4) + supporting systems

---

## 1. TECHNICAL RISKS

### 1.1 Latency Stacking

**Risk:** Pipeline chain (Vault → Core → Auditor → Assembler) accumulates latency.
Observed: 36–53s per query on local 7B model.

**Mitigation:**
- L0 Router bypasses pipeline for simple queries
- Vault retrieval is <50ms (ChromaDB local)
- Auditor is <1ms (regex, no LLM)
- Assembler is <1ms (string ops, no LLM)
- Primary bottleneck is L2 inference — irreducible for local models
- Consider quantized models (GGUF Q4) for faster inference

**Residual Risk:** LOW — latency is dominated by inference, not pipeline overhead.

### 1.2 Context Rot (Vault Dilution)

**Risk:** ChromaDB retrieves too many irrelevant documents, diluting the LLM's focus window.

**Mitigation:**
- Default retrieval limited to 5 documents
- Cosine similarity threshold filters low-relevance results
- Context is structured (facts/memory/constraints sections), not dumped raw
- Vault content is curated by explicit ingestion, not auto-scraped

**Residual Risk:** MEDIUM — requires monitoring. If response quality degrades, reduce n_results.

### 1.3 Schema Enforcement Failure

**Risk:** LLM fails to produce valid JSON despite Instructor enforcement. Instructor retries 3x,
but smaller models may fail consistently on complex schemas.

**Mitigation:**
- max_retries=3 (configurable)
- Fallback empty output with error flag
- Schema validated by Pydantic, not string matching
- Simpler models can use JSON mode with reduced schema

**Residual Risk:** LOW — Instructor handles this well. Monitor retry rates in audit log.

### 1.4 ChromaDB Corruption

**Risk:** Local ChromaDB store could corrupt (disk failure, interrupted write).

**Mitigation:**
- ChromaDB uses SQLite + HNSW internally — both have good corruption resistance
- Vault history is also stored as individual JSON files (backup)
- Full vault can be rebuilt from source files via re-ingestion

**Residual Risk:** LOW — rebuildable from source.

### 1.5 Model Drift / Degradation

**Risk:** Model updates (Ollama pull) could change behavior — more censored, less capable,
different output format.

**Mitigation:**
- Sovereignty Canary runs on boot, scores model health
- Canary results logged for trend detection
- Pin model versions in mirrorgate.yaml (e.g., `llama3.2:3b` not `latest`)
- Canary failures trigger visible warnings before inference begins

**Residual Risk:** LOW with canary. MEDIUM without.

### 1.6 Sycophancy Through Schema

**Risk:** LLM fills the `counterargument` field with weak objections to appear compliant
while still agreeing with flawed premises.

**Mitigation:**
- /challenge command triggers a dedicated adversarial second pass
- Auditor independently validates output content
- Persona prompt explicitly instructs honest disagreement
- Counterargument quality is ultimately a model capability issue — larger models do better

**Residual Risk:** MEDIUM — inherent to current LLM architectures. Schema forcing helps but doesn't eliminate.

---

## 2. OPERATIONAL RISKS

### 2.1 Single Point of Failure

**Risk:** All processing on one Mac Mini. Hardware failure = total outage.

**Mitigation:**
- Audit logs are append-only files — easy to backup
- ChromaDB is a directory — rsync to external drive
- Persona config is YAML in git — already backed up
- Recovery: clone repo + restore ChromaDB dir + reinstall deps

**Residual Risk:** MEDIUM — no HA, but recovery path is clear.

### 2.2 Disk Space Growth

**Risk:** Audit logs, ChromaDB, vault history grow unbounded.

**Mitigation:**
- Audit logs: rotate monthly (logrotate or manual)
- Vault history: cap at 1000 entries, oldest auto-pruned
- ChromaDB: monitor with `du -sh ~/.mirrorgate/vault/chromadb/`
- Canary logs: lightweight, negligible growth

**Residual Risk:** LOW with monitoring.

### 2.3 Ollama Availability

**Risk:** Ollama process crashes or isn't started. Pipeline fails silently.

**Mitigation:**
- Pipeline returns explicit InferenceError on connection failure
- Canary suite verifies Ollama on boot
- LaunchAgent can keep Ollama alive (launchd KeepAlive)

**Residual Risk:** LOW.

---

## 3. SECURITY RISKS

### 3.1 Prompt Injection

**Risk:** Malicious input attempts to override system prompt, extract instructions,
or manipulate structured output.

**Vectors:**
- "Ignore previous instructions" → override persona/constraints
- "Repeat your system prompt" → extract character definition
- Unicode homoglyphs → bypass regex filters
- JSON injection → corrupt structured output schema

**Mitigation:**
- Sanitizer blocks known injection patterns before inference
- Unicode normalization strips adversarial characters
- Instructor + Pydantic enforces output schema (can't inject arbitrary fields)
- System prompt extraction attempts are blocked and logged
- Output sanitizer checks for system prompt fragment leakage

**Residual Risk:** MEDIUM — novel injection attacks evolve. Keep patterns updated.

### 3.2 Audit Log Tampering

**Risk:** Hypervisor audit log (hypervisor.jsonl) is NOT cryptographically signed.
The existing MirrorGate crypto layer signs its audit records, but the Hypervisor
module doesn't yet use it.

**Mitigation (Current):**
- File permissions restrict write access
- Append-only pattern (no overwrites)

**Mitigation (Implemented v1.1):**
- Integrated with MirrorGate crypto layer (shared Ed25519 key pair)
- SHA-256 hash chain: `chain_hash = SHA256(sorted_json(record) + prev_hash)`
- Ed25519 signature on every chain_hash
- Separate chain state for Hypervisor log (`hypervisor_chain.json`)
- `/verify` command validates entire chain + signatures
- Tamper detection verified: modifying any record breaks the chain

**Residual Risk:** LOW — crypto signing fully operational.

### 3.3 Local Network Exposure

**Risk:** Ollama API binds to localhost:11434 with no authentication.
Any process on the machine can send inference requests.

**Mitigation:**
- Ollama defaults to 127.0.0.1 (localhost only)
- macOS firewall can restrict access
- MirrorGate server (port 8088) has API key auth
- The Hypervisor REPL is local-only (stdin/stdout)

**Residual Risk:** LOW — localhost-only is sufficient for single-user.

### 3.4 Dependency Supply Chain

**Risk:** Python packages (instructor, chromadb, openai, anthropic) could be
compromised via supply chain attack.

**Mitigation:**
- Pin exact versions in requirements.txt
- Use venv isolation (don't pollute system Python)
- Audit with `pip audit` periodically
- ChromaDB telemetry disabled in config
- No packages have network access beyond configured inference backends

**Residual Risk:** LOW — standard risk for any Python project. Pin and audit.

### 3.5 Data Exfiltration via Output

**Risk:** LLM could be prompted to include sensitive data (file paths, env vars,
API keys) in its response.

**Mitigation:**
- Output sanitizer checks for system leak patterns
- Existing MirrorGate output_schemas.yaml forbids password/api_key/secret fields
- Sovereignty constraints prevent external data transmission
- All responses are local (no network transmission from Hypervisor)

**Residual Risk:** LOW — output stays local.

---

## 4. LEGAL RISKS

### 4.1 Data Retention & Privacy

**Risk:** Vault stores conversation history (queries + summaries). Under GDPR (EU)
and CCPA (California), users have right to access, correct, and delete personal data.

**Current State:**
- All data is local (no cloud, no third-party processors)
- Data subject IS the data controller (Paul's own data)
- No third-party access or sharing

**Mitigations:**
- Vault history is individual JSON files — easy to inspect and delete
- `/clear` command wipes conversation history
- ChromaDB supports document deletion by ID
- No PII is transmitted to external services

**Legal Position:** STRONG for personal use. If the system ever processes OTHER people's
data (multi-user), GDPR compliance requires:
- Privacy policy
- Data processing agreement
- Right to deletion implementation
- Data minimization review

**Residual Risk:** NONE for personal sovereign use. HIGH if multi-user without modifications.

### 4.2 Model Licensing

**Risk:** Local models have various licenses with different restrictions.

| Model | License | Commercial Use | Restrictions |
|-------|---------|---------------|--------------|
| Llama 3.2 | Llama 3.2 Community License | Yes (< 700M MAU) | Must include attribution, can't use to train competing models |
| Qwen 2.5 | Apache 2.0 | Yes | Standard Apache terms |
| SmolLM3 | Apache 2.0 | Yes | Standard Apache terms |

**Mitigations:**
- Document which model is used in audit logs (model field in every record)
- Apache 2.0 models (Qwen, SmolLM) have minimal restrictions
- Llama license requires attribution if distributed — not applicable for local use

**Residual Risk:** LOW for personal use. Review before any commercial deployment.

### 4.3 Output Liability

**Risk:** System generates technical advice (security, architecture, code).
If advice is wrong and causes damage, who's liable?

**Legal Position:**
- LLM output is explicitly marked as untrusted (MirrorGate core principle)
- Auditor flags but doesn't guarantee correctness
- System philosophy: "Don't trust. Verify. Log. Prove."
- No warranty of correctness is implied

**Mitigations:**
- Audit trail proves what was generated and what was flagged
- Sovereignty audit catches the most dangerous category (cloud dependency recommendations)
- Canary system detects when model capabilities degrade
- User is the final decision-maker (human-in-the-loop)

**Residual Risk:** LOW for personal use. If offered as a service:
- Add explicit disclaimers
- Require user acknowledgment
- Professional liability insurance recommended

### 4.4 Derivative Work & IP

**Risk:** LLM-generated code could contain fragments from training data,
potentially creating copyright/IP issues.

**Mitigations:**
- Generated code is logged with model provenance
- For sensitive projects, use Apache 2.0 licensed models (cleaner training data provenance)
- Review generated code before committing to production
- MirrorGate audit trail provides evidence of generation context

**Residual Risk:** LOW — evolving legal landscape. Monitor case law.

---

## 5. ETHICAL RISKS

### 5.1 Echo Chamber / Filter Bubble

**Risk:** Evolution daemon adapts persona to match user's patterns. Over time,
the system reinforces existing thinking rather than challenging it.

**Mitigations:**
- Shadow Circuit (counterargument) forces opposing perspectives
- Evolution daemon is propose-only (human reviews changes)
- Persona includes explicit trait: "Pushes back when something doesn't add up"
- /challenge command for deliberate adversarial analysis

**Residual Risk:** MEDIUM — requires intentional use of challenge features.

### 5.2 Over-reliance / Automation Bias

**Risk:** User trusts system output without verification because the pipeline
"looks rigorous" (audit, sovereignty checks, structured output).

**Mitigations:**
- MirrorGate philosophy: "Don't trust. Verify."
- Audit log is proof of process, not proof of correctness
- Canary system is transparent about model limitations
- No "confidence score" on responses (avoids false precision)

**Residual Risk:** MEDIUM — human behavior, not system design. Mitigated by culture.

---

## 6. RISK MATRIX SUMMARY

| ID | Risk | Likelihood | Impact | Residual | Priority |
|----|------|-----------|--------|----------|----------|
| 1.1 | Latency stacking | HIGH | LOW | LOW | L0 Router built |
| 1.2 | Context rot | MEDIUM | MEDIUM | MEDIUM | Monitor |
| 1.3 | Schema failure | LOW | LOW | LOW | Instructor handles |
| 1.4 | ChromaDB corruption | LOW | MEDIUM | LOW | Rebuildable |
| 1.5 | Model degradation | MEDIUM | HIGH | LOW | Canary built |
| 1.6 | Sycophancy | HIGH | MEDIUM | MEDIUM | Schema + /challenge |
| 2.1 | Single point of failure | LOW | HIGH | MEDIUM | Backup plan |
| 2.2 | Disk growth | MEDIUM | LOW | LOW | Rotate logs |
| 2.3 | Ollama down | LOW | MEDIUM | LOW | LaunchAgent |
| 3.1 | Prompt injection | MEDIUM | HIGH | MEDIUM | Sanitizer built |
| 3.2 | Audit tampering | LOW | HIGH | **LOW** | Crypto wired (v1.1) |
| 3.3 | Network exposure | LOW | LOW | LOW | Localhost |
| 3.4 | Supply chain | LOW | HIGH | LOW | Pin + audit |
| 3.5 | Data exfiltration | LOW | MEDIUM | LOW | Output sanitizer |
| 4.1 | Privacy / GDPR | LOW | HIGH | NONE* | *Personal use only |
| 4.2 | Model licensing | LOW | MEDIUM | LOW | Apache 2.0 preferred |
| 4.3 | Output liability | LOW | HIGH | LOW | No warranty implied |
| 4.4 | IP / derivative work | LOW | MEDIUM | LOW | Monitor case law |
| 5.1 | Echo chamber | MEDIUM | MEDIUM | MEDIUM | Challenge features |
| 5.2 | Automation bias | MEDIUM | HIGH | MEDIUM | Cultural |

---

## 7. OPEN ITEMS (Requires Action)

1. ~~**CRITICAL:** Integrate Hypervisor audit log with MirrorGate crypto layer~~ **DONE** (v1.1)
2. **HIGH:** Implement log rotation for hypervisor.jsonl and canary.jsonl
3. **MEDIUM:** Add `pip audit` to CI/boot check
4. **MEDIUM:** Pin exact dependency versions (not minimum versions)
5. **LOW:** Add vault history pruning (cap at 1000 entries)

---

*This assessment covers the Hypervisor module as of v1.0.
Review quarterly or after significant architectural changes.*
