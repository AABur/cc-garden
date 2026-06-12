# detectors/repeated_reads.py
"""Flags files read more than 3 times in a single session (low-confidence hint)."""
from collections import Counter
from . import Leak

READ_THRESHOLD = 3
MIN_CONTENT_SIZE = 10_000  # suppress if small files


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    by_session: dict[str, list] = {}
    for ev in causal_events:
        if ev.tool_name not in {"Read", "Edit", "Write"} or not ev.file_path:
            continue
        by_session.setdefault(ev.session_id, []).append(ev)

    repeated = []
    for sess_id, events in by_session.items():
        counts = Counter(ev.file_path for ev in events)
        for path, count in counts.items():
            if count <= READ_THRESHOLD:
                continue
            total_size = sum(ev.content_size for ev in events if ev.file_path == path)
            if total_size >= MIN_CONTENT_SIZE:
                repeated.append((path, count, sess_id))

    if not repeated:
        return []

    evidence = [
        f"{path} accessed {count} times in session {sid[:8]}"
        for path, count, sid in repeated[:3]
    ]
    return [Leak(
        id="causal:repeated_reads",
        title="Repeated file reads in sessions",
        severity="suggestion",
        category="workflow",
        basis="causal",
        overlap_group="repeated_reads",
        additive=False,
        evidence=evidence + ["Consider caching file content in a variable or using /compact"],
        est_weekly_tokens=0,
        est_weekly_cost_usd=0.0,
        est_weekly_savings_usd=0.0,
        fix_action="Cache frequently-read file content within a session; use /compact to trim context",
    )]
