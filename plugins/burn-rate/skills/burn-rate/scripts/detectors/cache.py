# detectors/cache.py
"""Sessions with low cache-hit ratio AND large input — cache churn. Skips sessions
whose input is below the model's cacheable minimum (caching silently can't happen)."""
from __future__ import annotations
from detectors import Leak

MIN_INPUT = 500_000      # only worth flagging above this weekly input
LOW_RATIO = 0.5


def _session_totals(s):
    inp = cr = 0
    model_counts = {}
    for t in s.turns:
        if not t.usage:
            continue
        inp += t.usage.input_tokens
        cr += t.usage.cache_read_tokens
        if t.model:
            model_counts[t.model] = model_counts.get(t.model, 0) + 1
    model = max(model_counts, key=model_counts.get) if model_counts else None
    return inp, cr, model


def detect(sessions, config, pricing) -> list:
    flagged = []
    for s in sessions:
        inp, cr, model = _session_totals(s)
        denom = inp + cr
        if denom < MIN_INPUT:
            continue
        min_prefix = pricing.cacheable_minimum(model)
        if min_prefix and inp < min_prefix:
            continue
        ratio = cr / denom if denom else 0.0
        if ratio < LOW_RATIO:
            flagged.append((s, ratio, inp))
    if not flagged:
        return []
    worst = sorted(flagged, key=lambda x: x[1])[:3]
    total_input = sum(inp for _, _, inp in flagged)
    return [Leak(
        id="cache:low_hit_ratio",
        title=f"{len(flagged)} sessions with low cache-hit ratio",
        severity="warning", category="cache",
        evidence=[f"{s.project}/{s.session_id[:8]}: hit ratio {r:.0%}, input {inp:,}"
                  for s, r, inp in worst],
        est_weekly_tokens=total_input,
        fix_action="Avoid mid-session CLAUDE.md edits / project switching that invalidate the cached prefix; keep tools/system stable across the session.")]
