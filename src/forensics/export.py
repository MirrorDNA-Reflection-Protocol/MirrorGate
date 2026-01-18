"""
Session Export — Multiple format output

Formats:
- Markdown: Human-readable digest
- JSON: Full machine-parseable export
- (HTML: Interactive timeline - stretch goal)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .replay import SessionReplay, list_sessions


EXPORTS_DIR = Path.home() / ".mirrordna" / "forensics" / "exports"


def export_session(
    session_id: str,
    format: str = "md",
    output_path: Optional[str] = None
) -> str:
    """
    Export a session in specified format.
    
    Args:
        session_id: Session to export
        format: "md" or "json"
        output_path: Optional custom output path
        
    Returns:
        Path to exported file
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    replay = SessionReplay(session_id)
    
    if format.lower() == "md":
        content = _export_markdown(replay)
        ext = ".md"
    elif format.lower() == "json":
        content = _export_json(replay)
        ext = ".json"
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    if output_path:
        out_file = Path(output_path)
    else:
        out_file = EXPORTS_DIR / f"session-{session_id}{ext}"
    
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(content)
    
    return str(out_file)


def _export_markdown(replay: SessionReplay) -> str:
    """Export session as Markdown."""
    data = replay.session_data
    metrics = replay.metrics
    
    lines = [
        f"# Session Forensics Report",
        f"",
        f"**Session ID:** `{data.get('session_id')}`",
        f"**Started:** {data.get('started_at')}",
        f"**Ended:** {data.get('ended_at', 'In Progress')}",
        f"**Actor:** {data.get('actor')}",
        f"**Mode:** {data.get('context_mode')}",
        f"",
        f"---",
        f"",
        f"## Metrics",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Actions | {metrics.get('total_actions', 0)} |",
        f"| Blocked | {metrics.get('blocked_actions', 0)} |",
        f"| Rewrites | {metrics.get('rewrites', 0)} |",
        f"| Tripwires | {metrics.get('tripwires_triggered', 0)} |",
        f"| Avg Confidence | {metrics.get('avg_confidence', 0):.2%} |",
        f"",
        f"---",
        f"",
        f"## Actions Timeline",
        f"",
    ]
    
    for state in replay.iter_actions():
        action = state.action
        result_icon = {
            "ALLOW": "✅",
            "BLOCK": "⛔",
            "REWRITE": "📝"
        }.get(action.get("result", ""), "❓")
        
        lines.append(f"### Action {state.action_index + 1}: {action.get('action_type')}")
        lines.append(f"")
        lines.append(f"- **Time:** {action.get('timestamp')}")
        lines.append(f"- **Result:** {result_icon} {action.get('result')}")
        lines.append(f"- **Target:** `{action.get('target', 'N/A')}`")
        lines.append(f"- **Confidence:** {action.get('confidence', 0):.0%}")
        
        if action.get("content_preview"):
            lines.append(f"- **Preview:** {action.get('content_preview')[:50]}...")
        
        if state.decision_at_action:
            decision = state.decision_at_action
            lines.append(f"")
            lines.append(f"**Decision Point:**")
            lines.append(f"- Chosen: {decision.get('chosen')}")
            lines.append(f"- Alternatives: {', '.join(decision.get('alternatives', []))}")
            lines.append(f"- Rationale: {decision.get('rationale')}")
        
        lines.append(f"")
    
    if replay.decision_points:
        lines.extend([
            f"---",
            f"",
            f"## Decision Points Summary",
            f"",
            f"| # | Action | Chosen | Confidence |",
            f"|---|--------|--------|------------|",
        ])
        
        for i, dp in enumerate(replay.decision_points, 1):
            lines.append(
                f"| {i} | {dp.get('action_id', '')[:8]}... | "
                f"{dp.get('chosen')} | {dp.get('confidence', 0):.0%} |"
            )
    
    lines.extend([
        f"",
        f"---",
        f"",
        f"*Generated: {datetime.now().isoformat()}*",
    ])
    
    return "\n".join(lines)


def _export_json(replay: SessionReplay) -> str:
    """Export session as JSON."""
    data = replay.session_data.copy()
    
    # Add export metadata
    data["_export"] = {
        "format": "json",
        "version": "1.0",
        "exported_at": datetime.now().isoformat()
    }
    
    return json.dumps(data, indent=2, default=str)


def export_world_view(
    session_id: str,
    action_index: int,
    output_path: Optional[str] = None
) -> str:
    """
    Export world view at a specific action (for 2050 audit).
    """
    replay = SessionReplay(session_id)
    world_view = replay.get_world_view(action_index)
    
    lines = [
        f"# World View at Action {action_index}",
        f"",
        f"**Session:** `{session_id}`",
        f"**Timestamp:** {world_view.get('action', {}).get('timestamp')}",
        f"",
        f"---",
        f"",
        f"## What Was Known",
        f"",
        f"- Prior actions: {world_view.get('what_was_known', {}).get('prior_actions', 0)}",
        f"- Prior decisions: {world_view.get('what_was_known', {}).get('prior_decisions', 0)}",
        f"- Blocked so far: {world_view.get('what_was_known', {}).get('blocked_so_far', 0)}",
        f"",
        f"## Session Context",
        f"",
        f"- Mode: {world_view.get('session_context', {}).get('mode')}",
        f"- Actor: {world_view.get('session_context', {}).get('actor')}",
        f"",
        f"## Action Details",
        f"",
    ]
    
    action = world_view.get("action", {})
    lines.extend([
        f"- Type: {action.get('action_type')}",
        f"- Target: {action.get('target')}",
        f"- Result: {action.get('result')}",
        f"- Confidence: {world_view.get('confidence', 0):.0%}",
        f"",
        f"## Gate Results",
        f"",
    ])
    
    for gate in world_view.get("gate_results", []):
        lines.append(f"- {gate.get('gate', 'Unknown')}: {gate.get('result', 'Unknown')}")
    
    lines.extend([
        f"",
        f"## Reasoning",
        f"",
        f"{world_view.get('reasoning', 'Not recorded')}",
        f"",
        f"---",
        f"",
        f"*This is the world view at the time of decision.*",
        f"*Everything after this point was unknown.*",
    ])
    
    content = "\n".join(lines)
    
    if output_path:
        out_file = Path(output_path)
    else:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out_file = EXPORTS_DIR / f"worldview-{session_id}-{action_index}.md"
    
    out_file.write_text(content)
    return str(out_file)
