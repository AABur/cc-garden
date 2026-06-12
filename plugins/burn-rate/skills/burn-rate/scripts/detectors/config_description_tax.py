# detectors/config_description_tax.py
"""Skill/plugin descriptions load into context at session start on every turn.
ENABLE_TOOL_SEARCH defers MCP tools only -- NOT skills -- so N installed skills
impose a real per-turn context tax that tool-search does not reduce. This detector
measures that tax. Context-tax signal only, not priced."""
from __future__ import annotations
from . import Leak

MIN_DESCRIPTION_TOKENS = 2_000


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    if config is None:
        return []
    skill_tokens = getattr(config, "skill_description_tokens", 0)
    plugin_tokens = getattr(config, "plugin_description_tokens", 0)
    total_per_turn = skill_tokens + plugin_tokens
    if total_per_turn < MIN_DESCRIPTION_TOKENS:
        return []

    turns = sum(s.deduped_turn_count for s in sessions)
    est_weekly_tokens = total_per_turn * turns if turns else 0

    skill_count = getattr(config, "skill_count", 0)
    plugin_count = getattr(config, "plugin_count", 0)
    weights = getattr(config, "description_weight_by_plugin", {}) or {}
    top3 = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:3]

    evidence = [
        f"{skill_count} skills, {plugin_count} plugins installed",
        f"~{total_per_turn:,} description tokens load every turn "
        f"({skill_tokens:,} skills + {plugin_tokens:,} plugins)",
        f"Per-turn context tax: ~{total_per_turn:,} tokens before any work happens",
    ]
    if top3:
        evidence.append(
            "Top plugins by description weight: "
            + ", ".join(f"{name} (~{tok:,} tokens)" for name, tok in top3))
    if turns:
        evidence.append(
            f"~{est_weekly_tokens:,} tokens/week ({total_per_turn:,} × {turns} turns)")
    evidence.append(
        "Tool-search does NOT defer skill descriptions -- they load every turn "
        "regardless of ENABLE_TOOL_SEARCH. The fix is pruning/overrides, not "
        "enabling tool-search.")

    return [Leak(
        id="config:skill_description_tax",
        title=f"Skill/plugin descriptions cost ~{total_per_turn:,} tokens every turn",
        severity="suggestion",
        category="config",
        basis="mixed",
        overlap_group="config_tax",
        additive=False,
        evidence=evidence,
        est_weekly_tokens=est_weekly_tokens,
        est_weekly_cost_usd=0.0,
        est_weekly_savings_usd=0.0,
        fix_action=(
            "Set `disable-model-invocation: true` or add skill overrides in settings "
            "for rarely-used skills, and uninstall unused plugins to shrink the "
            "per-turn description tax."),
    )]
