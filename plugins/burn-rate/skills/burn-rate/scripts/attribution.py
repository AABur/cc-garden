# attribution.py
"""Aggregate deduped tokens by attribution dimension -> Pareto 'where to look first'."""
from __future__ import annotations


def by_dimension(sessions: list, attr: str) -> dict:
    """Sum total tokens grouped by a Turn attribute (e.g. 'attribution_skill',
    'attribution_plugin', 'attribution_agent', 'session_kind'). None -> 'interactive'
    for session_kind, else skipped."""
    totals: dict = {}
    for s in sessions:
        for t in s.turns:
            if not t.usage:
                continue
            key = getattr(t, attr, None)
            if key is None:
                if attr == "session_kind":
                    key = "interactive"
                else:
                    continue
            tok = (t.usage.input_tokens + t.usage.output_tokens + t.usage.cache_read_tokens
                   + t.usage.cache_write_5m_tokens + t.usage.cache_write_1h_tokens)
            totals[key] = totals.get(key, 0) + tok
    return totals


def top_n(totals: dict, n: int = 5) -> list:
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:n]
