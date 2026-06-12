# detectors/hook_injection_bloat.py
"""Detects hook injections that impose a recurring context tax.

Unlike tool_output_bloat (which measures tool_result output), this detector
measures the TRUE cost of hook-injected content. The observed events already
include every fire in the window, so the summed total IS the real per-week
injected cost -- no synthetic multiplier is applied (burn-rate's core
principle is a deduplicated, non-inflated basis)."""
from . import Leak

MIN_EST_TOKENS = 2_000   # ~8k chars/week of injection; below this is noise
PER_TURN_EVENTS = {"SessionStart", "UserPromptSubmit"}


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    # Group hook events by (hook_name, hook_event).
    groups: dict[tuple[str, str], dict] = {}
    for ev in causal_events:
        if ev.event_type != "hook":
            continue
        key = (ev.hook_name, ev.hook_event)
        g = groups.setdefault(key, {"fires": 0, "total_chars": 0})
        g["fires"] += 1
        g["total_chars"] += ev.content_size

    if not groups:
        return []

    # Rank by total_chars desc; the worst hook is the headline.
    ranked = sorted(groups.items(), key=lambda kv: kv[1]["total_chars"], reverse=True)

    worst_key, worst = ranked[0]
    worst_name, worst_event = worst_key
    worst_est_tokens = worst["total_chars"] // 4

    if worst_est_tokens <= MIN_EST_TOKENS:
        return []

    # Evidence: one bullet per top hook (up to 3).
    evidence = []
    for (name, event), g in ranked[:3]:
        fires = g["fires"]
        total_chars = g["total_chars"]
        est_tokens = total_chars // 4
        avg_chars = total_chars / fires
        evidence.append(
            f"{name} ({event}): fired {fires}×, {total_chars:,} chars total "
            f"(~{est_tokens:,} tok), avg {avg_chars:,.0f} chars/fire"
        )

    if worst_event in PER_TURN_EVENTS:
        evidence.append(
            "Note: SessionStart and UserPromptSubmit hooks inject on every qualifying "
            "turn, so their per-fire cost is paid repeatedly."
        )

    return [Leak(
        id="causal:hook_injection_bloat",
        title=f"Hook '{worst_name}' injects {worst_est_tokens:,} tokens/week into context",
        severity="warning",
        category="workflow",
        basis="causal",
        overlap_group="hook_tax",
        additive=False,
        evidence=evidence,
        est_weekly_tokens=worst_est_tokens,
        est_weekly_cost_usd=0.0,
        est_weekly_savings_usd=0.0,
        fix_action=(
            f"Review and trim the '{worst_name}' hook. For per-turn hooks, inject "
            "pointers (file paths) rather than full file contents so context stays lean."
        ),
    )]
