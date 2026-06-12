# detectors/hook_output_bloat.py
"""Detects sessions where hook output creates measurable context tax."""
from . import Leak

BLOAT_THRESHOLD_CHARS = 50_000    # aggregate tool_result content per session
MIN_SESSIONS = 3                   # noise filter


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    # Sum content_size for tool_result events, grouped by session_id.
    by_session: dict[str, int] = {}
    for ev in causal_events:
        if ev.event_type != "tool_result":
            continue
        by_session[ev.session_id] = by_session.get(ev.session_id, 0) + ev.content_size

    if len(by_session) < MIN_SESSIONS:
        return []

    total = sum(by_session.values())
    avg = total / len(by_session)

    if avg <= BLOAT_THRESHOLD_CHARS:
        return []

    # Top 3 sessions by content size for evidence.
    top3 = sorted(by_session.items(), key=lambda x: x[1], reverse=True)[:3]
    est_tokens = total // 4  # approximate chars-to-tokens ratio

    return [Leak(
        id="causal:hook_output_bloat",
        title="Large tool output injected into context",
        severity="warning",
        category="workflow",
        basis="causal",
        overlap_group="hook_bloat",
        additive=False,
        evidence=[
            f"{len(by_session)} sessions with tool_result events",
            f"Average tool output per session: {avg:,.0f} chars",
        ] + [f"{sid[:8]}: {size:,} chars" for sid, size in top3],
        est_weekly_tokens=est_tokens,
        est_weekly_cost_usd=0.0,
        est_weekly_savings_usd=0.0,
        fix_action="Review hook output size; large hook outputs are injected into context on every turn",
    )]
