# detectors/subagent_model_selection.py
"""Finds short Opus turns inside sidechain/subagent work — model routing opportunity.

This is the complementary detector to model_selection.py: it targets workflow/fan-out
turns (is_sidechain=True or session_kind='bg') rather than interactive turns.
Because subagent work is inherently active parallel workload, findings are always
'suggestion' severity rather than critical/warning.
"""
from __future__ import annotations
from . import Leak

OUTPUT_THRESHOLD = 1000
# Lower threshold than interactive (fan-out work has more variance per-session)
MIN_TURNS = 10


def detect(sessions, causal_events, config, pricing) -> list:
    simple = []
    for s in sessions:
        for t in s.turns:
            if not (t.usage and t.model and "opus" in t.model.lower()):
                continue
            # ONLY sidechain and bg workflow turns (opposite of model_selection.py)
            if not (t.is_sidechain or t.session_kind == "bg"):
                continue
            if t.usage.output_tokens < OUTPUT_THRESHOLD:
                simple.append(t)

    if len(simple) < MIN_TURNS:
        return []

    opus_cost = sonnet_cost = 0.0
    tokens = 0
    for t in simple:
        b = pricing.TokenBreakdown(
            input_tokens=t.usage.input_tokens,
            output_tokens=t.usage.output_tokens,
            cache_write_5m_tokens=t.usage.cache_write_5m_tokens,
            cache_write_1h_tokens=t.usage.cache_write_1h_tokens,
            cache_read_tokens=t.usage.cache_read_tokens,
        )
        opus_cost += pricing.estimate_cost(b, t.model)
        sonnet_cost += pricing.estimate_cost(b, "claude-sonnet-4-6")
        tokens += b.total

    savings = opus_cost - sonnet_cost
    severity = "suggestion"

    return [Leak(
        id="model_routing:subagent_opus_simple",
        title="Short Opus turns in subagent/fan-out work",
        severity=severity,
        category="model",
        basis="spend",
        overlap_group="model_routing",
        additive=False,
        evidence=[
            f"{len(simple)} short Opus turns in sidechain/background sessions",
            f"Opus cost: ${opus_cost:.2f}/week, Sonnet cost: ${sonnet_cost:.2f}/week",
            "This appears to be active parallel workload, not automatically a leak",
            f"Estimated model-routing opportunity: {tokens:,} tokens/week",
        ],
        est_weekly_tokens=tokens,
        est_weekly_cost_usd=round(opus_cost, 4),
        est_weekly_savings_usd=round(savings, 4),
        fix_action="Consider routing short worker turns to Sonnet; verify outputs are correct before switching",
    )]
