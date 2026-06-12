# detectors/workload_classifier.py
"""Classifies high-volume project activity; warns about automation only on multi-signal evidence."""
from __future__ import annotations
import statistics
from collections import Counter
from . import Leak

SESSIONS_PER_DAY_THRESHOLD = 10      # flag if any project exceeds this
AUTOMATION_INTERVAL_TOLERANCE = 0.20  # modal interval ± 20%
OFF_HOURS_THRESHOLD = 0.80            # 80% of sessions outside 08:00-22:00 UTC
INTERACTIVE_SHARE_THRESHOLD = 0.10    # < 10% interactive turns = suspicious
MIN_SESSIONS_FOR_AUTOMATION = 5       # need enough data for interval analysis
_INTERVAL_BUCKET = 1800              # 30-minute modal bucket (seconds)

ALL_SIGNAL_NAMES = (
    "stable_interval", "repeated_command", "single_cwd",
    "off_hours", "little_interactive",
)


def _inter_session_intervals(sessions):
    """Return sorted-by-start inter-session intervals (seconds) for timestamped sessions.

    Shared by the stable-interval signal and the cadence evidence so the two
    never diverge. Empty if fewer than 2 timestamped sessions exist.
    """
    timestamped = sorted(
        [s for s in sessions if s.first_timestamp is not None],
        key=lambda s: s.first_timestamp,
    )
    if len(timestamped) < 2:
        return []
    return [
        (timestamped[i + 1].first_timestamp - timestamped[i].first_timestamp).total_seconds()
        for i in range(len(timestamped) - 1)
    ]


def _sessions_per_day(sessions):
    """Return sessions/day for a project's session list (ignoring sessions without timestamps)."""
    timestamped = [s for s in sessions if s.first_timestamp is not None]
    if not timestamped:
        # No timestamps available; treat all sessions as occurring within one day.
        # This is a conservative upper bound — it may overcount but won't miss real spikes.
        return len(sessions)
    first = min(s.first_timestamp for s in timestamped)
    last = max(s.first_timestamp for s in timestamped)
    days = max(1.0, (last - first).total_seconds() / 86400)
    return len(sessions) / days


def _modal_interval(intervals):
    """Return the modal 30-minute-bucketed interval (seconds), or None if unavailable.

    Returns None when there are no intervals or the modal bucket is 0 (sessions
    clustered at the same instant), which carries no cadence information.
    """
    if not intervals:
        return None
    bucketed = [round(iv / _INTERVAL_BUCKET) * _INTERVAL_BUCKET for iv in intervals]
    modal_bucket = Counter(bucketed).most_common(1)[0][0]
    if modal_bucket == 0:
        return None
    return modal_bucket


def _signal_stable_interval(sessions):
    """True if >= 50% of inter-session intervals fall within modal ± 20%."""
    intervals = _inter_session_intervals(sessions)
    modal_bucket = _modal_interval(intervals)
    if modal_bucket is None:
        return False
    lo = modal_bucket * (1 - AUTOMATION_INTERVAL_TOLERANCE)
    hi = modal_bucket * (1 + AUTOMATION_INTERVAL_TOLERANCE)
    qualifying = sum(1 for iv in intervals if lo <= iv <= hi)
    return qualifying / len(intervals) >= 0.50


def _signal_repeated_command(sessions, causal_events):
    """True if a single bash command first-word appears in > 50% of bash causal events."""
    session_ids = {s.session_id for s in sessions}
    bash_events = [
        e for e in causal_events
        if e.session_id in session_ids and e.tool_name == "Bash" and e.command_head
    ]
    if not bash_events:
        return False
    first_words = [e.command_head.split()[0] for e in bash_events]
    if not first_words:
        return False
    counts = Counter(first_words)
    top_count = counts.most_common(1)[0][1]
    return top_count / len(bash_events) > 0.50


def _signal_single_cwd(sessions):
    """True if all sessions share exactly one unique cwd (no dir switching)."""
    cwds = {s.cwd for s in sessions if s.cwd}
    return len(cwds) == 1


def _signal_off_hours(sessions):
    """True if > OFF_HOURS_THRESHOLD fraction of sessions start between 22:00–08:00 UTC."""
    timestamped = [s for s in sessions if s.first_timestamp is not None]
    if not timestamped:
        return False
    off = sum(
        1 for s in timestamped
        if s.first_timestamp.hour >= 22 or s.first_timestamp.hour < 8
    )
    return off / len(timestamped) > OFF_HOURS_THRESHOLD


def _interactive_share(sessions):
    """Return fraction of turns that are interactive (not bg, not sidechain), 0..1."""
    total = 0
    interactive = 0
    for s in sessions:
        for t in s.turns:
            total += 1
            if t.session_kind != "bg" and not t.is_sidechain:
                interactive += 1
    return interactive / total if total else 0.0


def _signal_little_interactive(sessions):
    """True if < INTERACTIVE_SHARE_THRESHOLD of turns are interactive (not bg, not sidechain)."""
    total = sum(len(s.turns) for s in sessions)
    if total == 0:
        return False
    return _interactive_share(sessions) < INTERACTIVE_SHARE_THRESHOLD


def _compute_automation_signals(sessions, causal_events):
    """Return a list of (name, bool) for all 5 automation signals."""
    return [
        ("stable_interval", _signal_stable_interval(sessions)),
        ("repeated_command", _signal_repeated_command(sessions, causal_events)),
        ("single_cwd", _signal_single_cwd(sessions)),
        ("off_hours", _signal_off_hours(sessions)),
        ("little_interactive", _signal_little_interactive(sessions)),
    ]


def _model_mix_str(sessions):
    """Return a short model-mix string like 'opus: 3, sonnet: 12'."""
    combined: dict[str, int] = {}
    for s in sessions:
        for model, count in s.models_used.items():
            combined[model] = combined.get(model, 0) + count
    # Shorten model names to their recognizable short form.
    def _short(name):
        for part in ("opus", "sonnet", "haiku"):
            if part in name.lower():
                return part
        return name

    parts = sorted(combined.items(), key=lambda kv: kv[1], reverse=True)
    return ", ".join(f"{_short(m)}: {c}" for m, c in parts)


def _total_tokens(sessions):
    """Sum all token buckets across sessions."""
    total = 0
    for s in sessions:
        u = s.total_usage
        total += (u.input_tokens + u.output_tokens
                  + u.cache_read_tokens + u.cache_write_5m_tokens
                  + u.cache_write_1h_tokens)
    return total


def _sidechain_share(sessions):
    """Return fraction of turns that are sidechains."""
    total = sidechain = 0
    for s in sessions:
        for t in s.turns:
            total += 1
            if t.is_sidechain:
                sidechain += 1
    return sidechain / total if total else 0.0


def _off_hours_share(sessions):
    """Return fraction of timestamped sessions starting outside 08:00-22:00 UTC, 0..1.

    Mirrors the _signal_off_hours boundary (hour >= 22 or hour < 8). Returns 0.0
    when no session is timestamped.
    """
    timestamped = [s for s in sessions if s.first_timestamp is not None]
    if not timestamped:
        return 0.0
    off = sum(
        1 for s in timestamped
        if s.first_timestamp.hour >= 22 or s.first_timestamp.hour < 8
    )
    return off / len(timestamped)


def _interval_cv(intervals):
    """Return coefficient of variation (stddev/mean) as a 0..100 percentage, or None.

    Unavailable (None) when there are fewer than 2 intervals or the mean is 0.
    """
    if len(intervals) < 2:
        return None
    mean = statistics.mean(intervals)
    if mean == 0:
        return None
    return statistics.pstdev(intervals) / mean * 100


def _session_tokens(session):
    """Sum token buckets for a single session from its rolled-up total_usage.

    Reads total_usage only — consistent with _total_tokens and with how
    build_session_from_records populates it (total_usage is the sum of the
    session's per-turn usage). Summing per-turn usage on top of total_usage
    would double-count real sessions.
    """
    u = session.total_usage
    if u is None:
        return 0
    return (u.input_tokens + u.output_tokens
            + u.cache_read_tokens + u.cache_write_5m_tokens
            + u.cache_write_1h_tokens)


def _top_sessions_by_tokens(sessions, limit=2):
    """Return up to `limit` (session_id, tokens) pairs ranked by token total desc."""
    ranked = sorted(
        ((s.session_id, _session_tokens(s)) for s in sessions),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return ranked[:limit]


def cadence_evidence(proj_sessions):
    """Build human-readable cadence bullets shown on BOTH workload leak branches.

    Surfaces the underlying cadence data (modal interval, CV, off-hours, interactive
    and sidechain shares, top token sessions) so the user judges legitimate batch
    vs runaway — the classifier never asserts that on volume alone.
    """
    bullets = []

    intervals = _inter_session_intervals(proj_sessions)
    modal = _modal_interval(intervals)
    cv = _interval_cv(intervals)
    if modal is None or cv is None:
        bullets.append("Cadence: modal interval unavailable (<2 sessions)")
    else:
        bullets.append(f"Cadence: modal interval ~{modal:.0f}s (CV {cv:.0f}%)")

    off_pct = _off_hours_share(proj_sessions) * 100
    bullets.append(f"Off-hours: {off_pct:.0f}% (outside 08:00-22:00 UTC)")

    interactive_pct = _interactive_share(proj_sessions) * 100
    bullets.append(f"Interactive share: {interactive_pct:.0f}%")

    sc_share = _sidechain_share(proj_sessions)
    bullets.append(f"Sidechain share: {sc_share:.0%}")

    for sid, tokens in _top_sessions_by_tokens(proj_sessions):
        bullets.append(f"Top session by tokens: {sid[:8]} ({tokens:,} tok)")

    return bullets


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    if not sessions:
        return []

    # Group sessions by project name (Path(cwd).name).
    projects: dict[str, list] = {}
    for s in sessions:
        name = s.project
        projects.setdefault(name, []).append(s)

    leaks = []
    for project, proj_sessions in projects.items():
        rate = _sessions_per_day(proj_sessions)
        if rate <= SESSIONS_PER_DAY_THRESHOLD:
            continue

        signals = _compute_automation_signals(proj_sessions, causal_events)
        active_signals = [name for name, val in signals if val]
        absent_signals = [name for name in ALL_SIGNAL_NAMES if name not in active_signals]
        all_triggered = len(active_signals) == 5
        session_count = len(proj_sessions)
        tokens = _total_tokens(proj_sessions)
        mix = _model_mix_str(proj_sessions)
        cadence = cadence_evidence(proj_sessions)

        if all_triggered and session_count >= MIN_SESSIONS_FOR_AUTOMATION:
            leaks.append(Leak(
                id="workload:possible_recurring_automation",
                title=f"Possible recurring automation in project '{project}'",
                severity="warning",
                category="workload",
                basis="workload",
                additive=False,
                overlap_group="workload_classification",
                evidence=[
                    f"Project: {project}",
                    f"Sessions/day: {rate:.1f}",
                    f"Automation signals triggered: {', '.join(active_signals)}",
                    *cadence,
                ],
                est_weekly_tokens=tokens,
                est_weekly_cost_usd=0.0,
                est_weekly_savings_usd=0.0,
                fix_action=(
                    "Check for scheduled tasks (cron, launchd, GitHub Actions, `claude -p` loops)"
                ),
            ))
        else:
            absent_str = ", ".join(absent_signals) if absent_signals else "none"
            leaks.append(Leak(
                id="workload:high_volume_parallel_workload",
                title=f"High-volume parallel workload in project '{project}'",
                severity="suggestion",
                category="workload",
                basis="workload",
                additive=False,
                overlap_group="workload_classification",
                evidence=[
                    f"Project: {project}",
                    f"Sessions/day: {rate:.1f}",
                    f"Model mix: {mix}",
                    *cadence,
                    f"High-volume parallel workload, cadence shown above"
                    f" ({len(active_signals)}/5 automation signals triggered).",
                    f"NOT flagged as scheduled automation: absent signals are {absent_str}.",
                ],
                est_weekly_tokens=tokens,
                est_weekly_cost_usd=0.0,
                est_weekly_savings_usd=0.0,
                fix_action="No action needed unless cost is unexpectedly high",
                suggested_action=(
                    "If this is an unattended batch job, consider routing it to a local "
                    "model (e.g. Ollama) so it does not consume subscription headroom — "
                    "validate output quality on a parallel run first. This is a routing "
                    "suggestion, not a detected leak; no token/cost savings are claimed."
                ),
            ))

    return leaks
