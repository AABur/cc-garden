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

# prefix_rewrite_after_pause signal: a pause longer than this lets the cache
# prefix expire, so the next large turn has to rewrite the whole prefix.
PAUSE_SECONDS = 300            # > 5 min gap between consecutive turns
REWRITE_MIN_TOKENS = 50_000    # "large" cache-write that signals a prefix rewrite
MIN_REWRITES = 3               # noise filter on the number of pause->rewrite events


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


def _rewrite_tokens(usage) -> int:
    return usage.cache_write_5m_tokens + usage.cache_write_1h_tokens


def _detect_prefix_rewrites(sessions):
    """Find consecutive turn pairs where a >5min pause is followed by a large
    cache-write (prefix rewrite). Returns (events, peak_days).

    events: list of (session, gap_seconds, rewrite_tokens) — one per detected pause.
    peak_days: dict of UTC date -> total tokens, aggregated across all turns.
    """
    events = []
    peak_days = {}
    for s in sessions:
        timed = [t for t in s.turns if t.timestamp and t.usage]
        for t in timed:
            day = t.timestamp.date()
            peak_days[day] = peak_days.get(day, 0) + t.usage.context_size + t.usage.output_tokens
        timed.sort(key=lambda t: t.timestamp)
        for prev, cur in zip(timed, timed[1:]):
            gap = (cur.timestamp - prev.timestamp).total_seconds()
            rewrite = _rewrite_tokens(cur.usage)
            if gap > PAUSE_SECONDS and rewrite >= REWRITE_MIN_TOKENS:
                events.append((s, gap, rewrite))
    return events, peak_days


def _prefix_rewrite_leak(sessions):
    events, peak_days = _detect_prefix_rewrites(sessions)
    if len(events) < MIN_REWRITES:
        return None
    worst = sorted(events, key=lambda e: e[2], reverse=True)[:3]
    evidence = [f"{len(events)} pause→rewrite events detected (>5 min gap before a large cache-write)"]
    evidence += [f"{s.session_id[:8]}: {gap / 60:.0f} min pause, {rw:,} rewrite tokens"
                 for s, gap, rw in worst]
    for day, tok in sorted(peak_days.items(), key=lambda kv: kv[1], reverse=True)[:2]:
        evidence.append(f"Peak day: {day} ({tok:,} tok)")
    return Leak(
        id="cache:prefix_rewrite_after_pause",
        title=f"{len(events)} cache prefix rewrites after long pauses",
        severity="warning", category="cache",
        basis="spend", overlap_group="cache_efficiency", additive=False,
        evidence=evidence,
        est_weekly_tokens=sum(rw for _, _, rw in events),
        fix_action="A pause >5 min lets the cache prefix expire, so the next large turn "
                   "rewrites the whole prefix. Keep sessions active, or expect a rewrite "
                   "cost after long pauses.")


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

    leaks = []
    if flagged:
        worst = sorted(flagged, key=lambda x: x[1])[:3]
        total_input = sum(inp for _, _, inp in flagged)
        leaks.append(Leak(
            id="cache:low_hit_ratio",
            title=f"{len(flagged)} sessions with low cache-hit ratio",
            severity="warning", category="cache",
            basis="spend", overlap_group="cache_efficiency", additive=False,
            evidence=[f"{s.project}/{s.session_id[:8]}: hit ratio {r:.0%}, input {inp:,}"
                      for s, r, inp in worst],
            est_weekly_tokens=total_input,
            fix_action="Avoid mid-session CLAUDE.md edits / project switching that invalidate the cached prefix; keep tools/system stable across the session."))

    rewrite_leak = _prefix_rewrite_leak(sessions)
    if rewrite_leak:
        leaks.append(rewrite_leak)
    return leaks
