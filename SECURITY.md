# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

**security@n1intelligence.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Resolution Target**: Within 30 days for critical issues

## Security Principles

MirrorDNA is built with security as a core principle:

1. **No Silent Profiling** — All data collection requires explicit consent
2. **Local-First** — Sensitive data stays on user devices by default
3. **Cryptographic Integrity** — State changes are signed and verifiable
4. **Minimal Attack Surface** — No unnecessary network exposure
5. **Audit Trail** — All operations are logged for transparency

## Known Security Considerations

- API keys should never be committed to repositories
- Use environment variables for sensitive configuration
- Validate all inputs at system boundaries
- Review MirrorGate enforcement rules before deployment

## Bug Bounty

We appreciate security researchers who help keep MirrorDNA secure. While we don't have a formal bug bounty program, we will:

- Credit researchers in release notes (with permission)
- Provide a reference letter upon request
- Consider swag/merchandise for significant findings

---

*Part of the [MirrorDNA Ecosystem](https://github.com/MirrorDNA-Reflection-Protocol)*
