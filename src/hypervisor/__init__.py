"""
MirrorGate Hypervisor — Assembly Line Inference Pipeline

L0: Router     — Fast path classification
L1: Vault      — Context injection (ChromaDB)
L2: Core       — Structured inference (Instructor + Pydantic)
L3: Auditor    — Independent validation (pattern scanning)
L4: Assembler  — Persona rendering (characterful output)

Supporting:
  Sanitizer  — Input/output defense
  Canary     — Boot-time model health check
  Evolution  — Persona drift detection
"""

__version__ = "1.1.0"
