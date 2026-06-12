"""CLAUDE.md files over the ~2k-token target (paid on every turn). The 2k target is
cited from Anthropic's cost doc but not re-confirmed for 2026 — flagged as such."""
from __future__ import annotations
from detectors import Leak

TARGET = 2000
CRITICAL = 5000


def detect(sessions, causal_events, config, pricing) -> list:
    if config is None:
        return []
    total_turns = sum(s.deduped_turn_count for s in sessions)
    leaks = []
    for path, tokens in getattr(config, "claude_md_tokens", {}).items():
        if tokens <= TARGET:
            continue
        severity = "critical" if tokens > CRITICAL else "warning"
        # CLAUDE.md is re-sent on every turn, so the true weekly cost is
        # tokens × all turns this week, not just the file size alone.
        weekly = tokens * total_turns
        leaks.append(Leak(
            id=f"claude_md:bloat:{path}",
            title=f"CLAUDE.md over target (~{tokens:,} tokens)",
            severity=severity, category="claude_md",
            basis="mixed", overlap_group="prompt_tax", additive=False,
            evidence=[f"{path}: ~{tokens:,} tokens (target ~{TARGET}, cited but not re-confirmed for 2026)",
                      f"~{weekly:,} tokens/week ({tokens:,} × {total_turns} turns)",
                      "Non-English structural content tokenizes 2-3x heavier — keep rules in English"],
            est_weekly_tokens=weekly,
            fix_action="Move command recipes/playbooks into separate files loaded on demand via @filename; keep stable rules inline."))
    return leaks
