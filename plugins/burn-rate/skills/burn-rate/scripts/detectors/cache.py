# detectors/cache.py
"""Sessions with a low cache-hit ratio AND a large prompt — cache churn. Skips
sessions whose per-turn prompt is below the model's cacheable minimum (caching
silently can't happen, so a low ratio there is not the user's fault)."""
from __future__ import annotations
from detectors import Leak

# Size gate: a session's input + cache-read total below this is too small to matter.
MIN_INPUT = 500_000
# Flag when fewer than half the context tokens are cache hits — below this the
# session is repeatedly re-sending an uncached prefix instead of reusing it.
LOW_RATIO = 0.5


def _session_totals(s):
    inp = cr = turns = 0
    model_counts = {}
    for t in s.turns:
        if not t.usage:
            continue
        turns += 1
        inp += t.usage.input_tokens
        cr += t.usage.cache_read_tokens
        if t.model:
            model_counts[t.model] = model_counts.get(t.model, 0) + 1
    model = max(model_counts, key=model_counts.get) if model_counts else None
    return inp, cr, model, turns


def detect(sessions, causal_events, config, pricing) -> list:
    flagged = []
    for s in sessions:
        inp, cr, model, turns = _session_totals(s)
        denom = inp + cr
        if denom < MIN_INPUT:
            continue
        # Caching is a per-turn prefix concern: compare the AVERAGE prompt per turn
        # (denom / turns, i.e. input + cache-read) against the model's cacheable
        # minimum, not the session total. A session of many tiny-prompt turns can't
        # cache even though the session-wide total is large.
        min_prefix = pricing.cacheable_minimum(model)
        if min_prefix and turns and denom < min_prefix * turns:
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
        basis="spend", overlap_group="cache_efficiency", additive=False,
        evidence=[f"{s.project}/{s.session_id[:8]}: hit ratio {r:.0%}, input {inp:,}"
                  for s, r, inp in worst],
        est_weekly_tokens=total_input,
        fix_action="Avoid mid-session CLAUDE.md edits / project switching that invalidate the cached prefix; keep tools/system stable across the session.")]
