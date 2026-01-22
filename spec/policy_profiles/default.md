# DEFAULT Policy Profile

The `DEFAULT` profile is the baseline for all MirrorGate interactions. It prioritizes safety and reflection over brevity or direct action.

---

## 🛠 Configuration

```yaml
profile: DEFAULT
version: 1.0.0
description: "Baseline reflective safety profile."

prefilters:
  - id: classify_intent
    config:
      sensitive_domains: [medical, legal, financial, crisis, self-harm]
      action: elevate_to_strict
  - id: high_risk_guard
    config:
      block_prescriptive: true

postfilters:
  - id: forbid_prescriptive_language
    config:
      disallowed_patterns:
        - "you should"
        - "do this"
        - "the best option is"
        - "I recommend"
  - id: enforce_uncertainty
    config:
      markers: ["perhaps", "it's possible", "I'm unsure if", "one reflection is"]
  - id: enforce_reflective_schema
    config:
      mandatory_glyphs: [⟡, ⧈, ⧉]
      reflection_tags: true

backend:
  allowed_modes: [local, cloud]
  default_mode: local
```

---

## 📝 Change Log

- **v1.0.0**: Initial release. Standardized sensitive domain classification.
