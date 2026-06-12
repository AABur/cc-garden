# detectors/bash_antipatterns.py
"""Flags shell reads/searches where native Claude Code tools would be cheaper."""
from . import Leak

SHELL_READERS = {"cat", "head", "tail", "sed", "awk", "grep", "find"}
# Each shell reader mapped to the cheaper native Claude Code tool.
NATIVE_TOOL = {
    "grep": "Grep",
    "find": "Glob",
    "cat": "Read", "head": "Read", "tail": "Read",
    "sed": "Edit", "awk": "Edit",
}
MIN_COUNT = 10   # noise filter


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    matches = []
    per_command = {}
    for ev in causal_events:
        if ev.tool_name != "Bash" or not ev.command_head:
            continue
        first_word = ev.command_head.strip().split()[0] if ev.command_head.strip() else ""
        if first_word in SHELL_READERS:
            matches.append(ev)
            per_command[first_word] = per_command.get(first_word, 0) + 1
    if len(matches) < MIN_COUNT:
        return []
    # Per-command breakdown bullets, one per command seen, sorted by count desc,
    # each pointing at its native Claude Code equivalent.
    breakdown = [
        f"{cmd} ×{count} → use {NATIVE_TOOL[cmd]}"
        for cmd, count in sorted(per_command.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return [Leak(
        id="causal:bash_antipatterns",
        title="Shell reads/searches in Claude Code",
        severity="suggestion",
        category="workflow",
        basis="causal",
        overlap_group="bash_patterns",
        additive=False,
        evidence=[
            f"{len(matches)} shell read/search calls detected (cat/head/tail/sed/awk/grep/find)",
            *breakdown,
            "In Claude Code, native Read/Grep tools are cheaper and bypass the shell overhead",
            "Some calls may be intentional (e.g. piped commands, complex transformations)",
        ],
        est_weekly_tokens=0,
        est_weekly_cost_usd=0.0,
        est_weekly_savings_usd=0.0,
        fix_action="Prefer Read, Grep, and other native Claude Code tools over shell equivalents when possible",
    )]
