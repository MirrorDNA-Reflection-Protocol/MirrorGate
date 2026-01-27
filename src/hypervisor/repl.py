"""
Interactive REPL for the Hypervisor.

This is the conversational interface. The user talks to the persona.
Under the hood: Router → Vault → Core → Auditor → Assembler.

Commands:
  /trace     — toggle cognitive trace (reasoning + counterargument)
  /audit     — toggle audit details
  /status    — pipeline status + canary health
  /clear     — clear conversation history
  /challenge — adversarial second pass on last query
  /canary    — run the sovereignty canary suite
  /evolve    — check for persona evolution proposals
  /route     — show how the last query was routed
  /verify    — verify audit log chain integrity
  /quit      — exit
"""

from __future__ import annotations
import os
import sys
import argparse
from pathlib import Path

import yaml

from .pipeline import Pipeline, PipelineConfig
from .evolution import Evolution
from .canary import HealthStatus


BANNER = """
 ┌──────────────────────────────────────────┐
 │   MIRRORGATE HYPERVISOR v1.1             │
 │   Assembly Line Inference                │
 │                                          │
 │   /trace     — toggle trace view         │
 │   /audit     — toggle audit view         │
 │   /status    — pipeline + canary status   │
 │   /challenge — adversarial second pass   │
 │   /canary    — run model health check    │
 │   /evolve    — persona evolution check   │
 │   /route     — show last route decision  │
 │   /verify    — verify audit chain        │
 │   /clear     — clear history             │
 │   /quit      — exit                      │
 └──────────────────────────────────────────┘
"""


def load_config_from_yaml(path: str) -> dict:
    """Load pipeline config from mirrorgate.yaml."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        raw = yaml.safe_load(p.read_text())
        if not isinstance(raw, dict):
            return {}
        return raw
    except Exception:
        return {}


def build_config(args: argparse.Namespace) -> PipelineConfig:
    """Build PipelineConfig from CLI args + YAML config."""
    yaml_path = args.config if hasattr(args, "config") else None
    yaml_config = {}
    if yaml_path:
        yaml_config = load_config_from_yaml(yaml_path)
    else:
        for candidate in [
            Path.cwd() / "mirrorgate.yaml",
            Path.home() / "repos" / "mirrorgate" / "mirrorgate.yaml",
            Path.home() / ".mirrorgate" / "config.yaml",
        ]:
            if candidate.exists():
                yaml_config = load_config_from_yaml(str(candidate))
                break

    # Extract inference config
    inference = yaml_config.get("inference", {})
    backends = inference.get("backends", [])
    default_backend = inference.get("default", "local")

    backend_config = {}
    for b in backends:
        if b.get("name") == default_backend:
            backend_config = b
            break

    backend_type = getattr(args, "backend", None) or backend_config.get("type", "ollama")
    model = getattr(args, "model", None) or backend_config.get("model", "llama3.2")

    # Determine base_url for ollama
    base_url = getattr(args, "base_url", None)
    if not base_url and backend_type == "ollama":
        base_url = "http://localhost:11434/v1"

    # Hypervisor-specific config
    hv = yaml_config.get("hypervisor", {})

    return PipelineConfig(
        backend=backend_type,
        model=model,
        base_url=base_url,
        api_key=getattr(args, "api_key", None) or os.environ.get("ANTHROPIC_API_KEY"),
        persona_path=getattr(args, "persona", None) or hv.get("persona_path"),
        vault_dir=hv.get("vault_dir"),
        strict_audit=getattr(args, "strict", False) or hv.get("strict_audit", False),
        strict_sanitizer=getattr(args, "strict_sanitizer", False),
        show_trace=getattr(args, "trace", False),
        show_audit=getattr(args, "show_audit", False),
        max_retries=hv.get("max_retries", 3),
        run_canary=getattr(args, "canary", False),
    )


def run_repl(config: PipelineConfig):
    """Run the interactive conversation loop."""
    pipeline = Pipeline(config)
    evolution = Evolution(
        persona_path=config.persona_path or str(
            Path.home() / "repos" / "mirrorgate" / "config" / "persona.yaml"
        )
    )
    last_query = ""
    last_route = None

    print(BANNER)
    print(f"  Backend: {config.backend} / {config.model}")
    print(f"  Persona: {pipeline.persona.name}")
    print(f"  Strict:  audit={config.strict_audit} sanitizer={config.strict_sanitizer}")

    # Run canary on boot if requested
    if config.run_canary:
        print("\n  Running canary suite...")
        report = pipeline.run_canary_suite()
        _print_canary_report(report)
        if report.status == HealthStatus.COMPROMISED:
            print("\n  \033[31mCORE COMPROMISED. Model is too censored for reliable output.\033[0m")
            print("  \033[31mProceeding with extreme caution.\033[0m")
        elif report.status == HealthStatus.IMPAIRED:
            print("\n  \033[33mModel capabilities impaired. Some responses may be degraded.\033[0m")

    print()

    while True:
        try:
            user_input = input(f"\033[36myou>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]

            if cmd in ("/quit", "/exit", "/q"):
                break

            elif cmd == "/trace":
                pipeline.assembler.show_trace = not pipeline.assembler.show_trace
                state = "on" if pipeline.assembler.show_trace else "off"
                print(f"  Trace view: {state}")
                continue

            elif cmd == "/audit":
                pipeline.assembler.show_audit = not pipeline.assembler.show_audit
                state = "on" if pipeline.assembler.show_audit else "off"
                print(f"  Audit view: {state}")
                continue

            elif cmd == "/status":
                _print_status(pipeline)
                continue

            elif cmd == "/challenge":
                if not last_query:
                    print("  No previous query to challenge.")
                    continue
                print(f"  Challenging: \"{last_query[:60]}...\"")
                result = pipeline.challenge(last_query)
                if result.error:
                    print(f"\033[31m  Error: {result.error}\033[0m")
                else:
                    print(f"\n\033[31m{pipeline.persona.name} [CHALLENGE]>\033[0m {result.response}")
                    print(f"\033[90m  [{result.latency_ms:.0f}ms | adversarial]\033[0m")
                print()
                continue

            elif cmd == "/canary":
                print("  Running canary suite...")
                report = pipeline.run_canary_suite()
                _print_canary_report(report)
                print()
                continue

            elif cmd == "/evolve":
                parts = user_input.split()
                subcmd = parts[1] if len(parts) > 1 else "check"
                _handle_evolve(evolution, subcmd)
                continue

            elif cmd == "/route":
                if last_route:
                    print(f"  Last route: {last_route.tier.value}")
                    print(f"  Reason: {last_route.reason}")
                    print(f"  Tokens: {last_route.token_count}")
                else:
                    print("  No route recorded yet.")
                continue

            elif cmd == "/verify":
                print("  Verifying audit chain...")
                result = pipeline.verify_chain()
                if result.valid:
                    print(f"  \033[32mCHAIN VALID\033[0m — {result.records_checked} records verified")
                    if result.signature_failures > 0:
                        print(f"  \033[33mWarning: {result.signature_failures} signature verification failures\033[0m")
                else:
                    print(f"  \033[31mCHAIN BROKEN\033[0m at record {result.broken_at}")
                    print(f"  Error: {result.error}")
                    print(f"  Records before break: {result.records_checked}")
                # Show chain status
                status = pipeline.crypto.get_chain_status()
                print(f"  Records: {status['records']}")
                print(f"  Last hash: {status['last_hash']}")
                print(f"  Keys: {'present' if status['keys_present'] else 'MISSING'}")
                continue

            elif cmd == "/clear":
                pipeline.clear_history()
                last_query = ""
                last_route = None
                print("  History cleared.")
                continue

            elif cmd == "/help":
                print(BANNER)
                continue

            else:
                print(f"  Unknown command: {cmd}")
                continue

        # Route and run the pipeline
        last_query = user_input
        last_route = pipeline.router.route(user_input)
        result = pipeline.run(user_input)

        # Display
        if result.error:
            print(f"\033[31m  Error: {result.error}\033[0m")
        else:
            # Show counterargument if trace is on
            trace_suffix = ""
            if pipeline.assembler.show_trace and result.output.trace.counterargument:
                trace_suffix = f"\n\033[90m  Counterargument: {result.output.trace.counterargument}\033[0m"

            print(f"\n\033[33m{pipeline.persona.name}>\033[0m {result.response}{trace_suffix}")
            print(f"\033[90m  [{result.latency_ms:.0f}ms | {result.tier} | {result.output.meta.intent.value} | risk:{result.verdict.risk_score:.1f}]\033[0m")

            # Show sanitizer warnings if any
            if result.sanitizer_warnings:
                for w in result.sanitizer_warnings:
                    print(f"\033[33m  Warning: {w}\033[0m")

        print()


def _print_status(pipeline: Pipeline):
    """Display pipeline status."""
    print(f"  Persona:    {pipeline.persona.name}")
    print(f"  Backend:    {pipeline.core.backend}")
    print(f"  Model:      {pipeline.core.model}")
    print(f"  History:    {len(pipeline.history)} exchanges")
    print(f"  Trace:      {'on' if pipeline.assembler.show_trace else 'off'}")
    print(f"  Audit:      {'on' if pipeline.assembler.show_audit else 'off'}")
    print(f"  Strict:     audit={pipeline.auditor.strict}")
    # Canary
    if pipeline.canary_report:
        print(f"  Canary:     {pipeline.canary_report.status.value} ({pipeline.canary_report.score:.0f}%)")
    else:
        print(f"  Canary:     not run (use /canary)")
    # Chain status
    chain = pipeline.crypto.get_chain_status()
    print(f"  Chain:      {chain['records']} signed records | keys={'yes' if chain['keys_present'] else 'NO'}")


def _print_canary_report(report):
    """Display canary report."""
    color = {
        HealthStatus.HEALTHY: "\033[32m",
        HealthStatus.DEGRADED: "\033[33m",
        HealthStatus.IMPAIRED: "\033[33m",
        HealthStatus.COMPROMISED: "\033[31m",
    }.get(report.status, "")
    reset = "\033[0m"

    print(f"\n  {color}--- CANARY REPORT ---{reset}")
    print(report.summary)
    print(f"  {color}--- END REPORT ---{reset}")


def _handle_evolve(evolution: Evolution, subcmd: str):
    """Handle /evolve subcommands."""
    if subcmd == "check":
        pattern = evolution.analyze()
        if pattern is None:
            print("  Not enough conversation history for analysis (need 10+).")
            return
        print(f"  Analyzed {pattern.total_queries} queries:")
        print(f"    Technical density: {pattern.technical_density:.0%}")
        print(f"    Question ratio:    {pattern.question_ratio:.0%}")
        print(f"    Command ratio:     {pattern.command_ratio:.0%}")
        print(f"    Reflection ratio:  {pattern.reflection_ratio:.0%}")
        print(f"    Topics: {pattern.topic_distribution}")

        diff = evolution.propose(pattern)
        if diff:
            print(f"\n  Proposal generated: {diff.id}")
            for c in diff.changes:
                print(f"    [{c['action'].upper()}] {c['field']}: {c['reason']}")
            print(f"\n  Review: /evolve proposals")
            print(f"  Apply:  /evolve apply")
        else:
            print("  No persona changes suggested — current config fits usage patterns.")

    elif subcmd == "proposals":
        proposals = evolution.get_pending_proposals()
        if not proposals:
            print("  No pending proposals.")
            return
        for p in proposals:
            print(f"  {p.name}")

    elif subcmd == "apply":
        proposals = evolution.get_pending_proposals()
        if not proposals:
            print("  No pending proposals to apply.")
            return
        latest = proposals[-1]
        print(f"  Applying: {latest.name}")
        if evolution.apply_proposal(latest):
            print("  Applied. Previous persona backed up.")
        else:
            print("  Failed to apply.")

    elif subcmd == "reject":
        proposals = evolution.get_pending_proposals()
        if not proposals:
            print("  No pending proposals to reject.")
            return
        latest = proposals[-1]
        evolution.reject_proposal(latest)
        print(f"  Rejected: {latest.name}")

    else:
        print(f"  Usage: /evolve [check|proposals|apply|reject]")


def main():
    parser = argparse.ArgumentParser(
        description="MirrorGate Hypervisor — Conversational Inference Pipeline"
    )
    parser.add_argument("--backend", choices=["ollama", "anthropic", "openai"],
                        help="Inference backend")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--base-url", help="Base URL for API")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--persona", help="Path to persona YAML")
    parser.add_argument("--config", help="Path to mirrorgate.yaml")
    parser.add_argument("--strict", action="store_true", help="Strict audit mode")
    parser.add_argument("--strict-sanitizer", action="store_true", help="Strict input sanitization")
    parser.add_argument("--trace", action="store_true", help="Show cognitive trace")
    parser.add_argument("--show-audit", action="store_true", help="Show audit details")
    parser.add_argument("--canary", action="store_true", help="Run canary suite on boot")

    args = parser.parse_args()
    config = build_config(args)
    run_repl(config)


if __name__ == "__main__":
    main()
