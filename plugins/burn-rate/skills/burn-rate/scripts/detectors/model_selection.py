# detectors/model_selection.py
"""Opus used on interactive simple turns (output < 1k), excluding workflow/subagent
turns (those are a separate fan-out concern). Output length is a weak proxy, so this
is a signal to investigate, not proof."""
from __future__ import annotations
from detectors import Leak

OUTPUT_THRESHOLD = 1000
# Minimum sample before the weak output-length proxy is worth surfacing — fewer
# short Opus turns than this is noise, not a pattern.
MIN_TURNS = 30


def detect(sessions, causal_events, config, pricing) -> list:
    simple = []
    for s in sessions:
        for t in s.turns:
            if not (t.usage and t.model and "opus" in t.model.lower()):
                continue
            if t.is_sidechain or t.session_kind == "bg":
                continue
            if t.usage.output_tokens < OUTPUT_THRESHOLD:
                simple.append(t)
    if len(simple) < MIN_TURNS:
        return []
    opus_cost = sonnet_cost = 0.0
    tokens = 0
    for t in simple:
        b = pricing.TokenBreakdown(
            input_tokens=t.usage.input_tokens, output_tokens=t.usage.output_tokens,
            cache_read_tokens=t.usage.cache_read_tokens,
            cache_write_5m_tokens=t.usage.cache_write_5m_tokens,
            cache_write_1h_tokens=t.usage.cache_write_1h_tokens)
        opus_cost += pricing.estimate_cost(b, t.model)
        sonnet_cost += pricing.estimate_cost(b, "claude-sonnet-4-6")
        tokens += b.total
    savings = round(opus_cost - sonnet_cost, 2)
    severity = "critical" if savings >= 5 else "warning" if savings >= 1 else "suggestion"
    return [Leak(
        id="model_routing:interactive_opus_simple",
        title=f"Opus on {len(simple)} interactive simple turns",
        severity=severity, category="model",
        basis="spend",
        overlap_group="model_routing",
        additive=False,
        evidence=[f"{len(simple)} interactive Opus turns with <{OUTPUT_THRESHOLD} output tokens",
                  "Excludes workflow/subagent turns (separate concern)",
                  f"Opus est ${opus_cost:.2f} vs Sonnet est ${sonnet_cost:.2f} (weekly, list)"],
        est_weekly_tokens=tokens, est_weekly_cost_usd=round(opus_cost, 2),
        est_weekly_savings_usd=savings,
        fix_action="Set project default model to Sonnet in .claude/settings.json; escalate to Opus only for hard reasoning.")]
