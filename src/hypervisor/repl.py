"""
Interactive REPL for the Hypervisor.

This is the conversational interface. The user talks to the persona.
Under the hood: Vault → Core → Auditor → Assembler.
"""

from __future__ import annotations
import os
import sys
import argparse
from pathlib import Path

import yaml

from .pipeline import Pipeline, PipelineConfig


BANNER = """
 ┌─────────────────────────────────┐
 │   MIRRORGATE HYPERVISOR v1.0    │
 │   Assembly Line Inference       │
 │                                 │
 │   /trace  — toggle trace view   │
 │   /audit  — toggle audit view   │
 │   /status — pipeline status     │
 │   /clear  — clear history       │
 │   /quit   — exit                │
 └─────────────────────────────────┘
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
        show_trace=getattr(args, "trace", False),
        show_audit=getattr(args, "show_audit", False),
        max_retries=hv.get("max_retries", 3),
    )


def run_repl(config: PipelineConfig):
    """Run the interactive conversation loop."""
    pipeline = Pipeline(config)

    print(BANNER)
    print(f"  Backend: {config.backend} / {config.model}")
    print(f"  Persona: {pipeline.persona.name}")
    print(f"  Strict:  {config.strict_audit}")
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
            elif cmd == "/clear":
                pipeline.clear_history()
                print("  History cleared.")
                continue
            elif cmd == "/help":
                print(BANNER)
                continue
            else:
                print(f"  Unknown command: {cmd}")
                continue

        # Run the pipeline
        result = pipeline.run(user_input)

        # Display
        if result.error:
            print(f"\033[31m  Error: {result.error}\033[0m")
        else:
            print(f"\n\033[33m{pipeline.persona.name}>\033[0m {result.response}")
            print(f"\033[90m  [{result.latency_ms:.0f}ms | {result.output.meta.intent.value} | risk:{result.verdict.risk_score:.1f}]\033[0m")
        print()


def _print_status(pipeline: Pipeline):
    """Display pipeline status."""
    print(f"  Persona:    {pipeline.persona.name}")
    print(f"  Backend:    {pipeline.core.backend}")
    print(f"  Model:      {pipeline.core.model}")
    print(f"  History:    {len(pipeline.history)} exchanges")
    print(f"  Trace:      {'on' if pipeline.assembler.show_trace else 'off'}")
    print(f"  Audit:      {'on' if pipeline.assembler.show_audit else 'off'}")
    print(f"  Strict:     {pipeline.auditor.strict}")


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
    parser.add_argument("--trace", action="store_true", help="Show cognitive trace")
    parser.add_argument("--show-audit", action="store_true", help="Show audit details")

    args = parser.parse_args()
    config = build_config(args)
    run_repl(config)


if __name__ == "__main__":
    main()
