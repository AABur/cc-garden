# detectors/context_rot.py
"""Turns past the ~400k context-rot zone (Thariq Shihipar, Anthropic): attention
degrades and re-feeding is expensive. Counts over-threshold turns and excess tokens."""
from __future__ import annotations
from detectors import Leak

ZONE = 400_000
MIN_TURNS = 10


def detect(sessions, config, pricing) -> list:
    over = 0
    excess = 0
    peak = 0
    for s in sessions:
        for t in s.turns:
            if not t.usage:
                continue
            ctx = t.usage.context_size
            peak = max(peak, ctx)
            if ctx > ZONE:
                over += 1
                excess += ctx - ZONE
    if over < MIN_TURNS:
        return []
    return [Leak(
        id="context:rot_zone",
        title=f"{over} turns past the {ZONE // 1000}k context-rot zone",
        severity="warning", category="context",
        evidence=[f"{over} turns over {ZONE // 1000}k context (peak {peak // 1000}k)",
                  f"~{excess:,} excess tokens re-fed past the threshold",
                  "Thariq (Anthropic): the model is least intelligent when compacting late"],
        est_weekly_tokens=excess,
        fix_action="Compact proactively with a scope hint (`/compact focus on X, drop Y`) or start a new session per task.")]
