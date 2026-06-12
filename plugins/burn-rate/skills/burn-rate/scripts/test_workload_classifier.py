# test_workload_classifier.py
"""Tests for the workload_classifier detector."""
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import Turn, Usage, Session, CausalEvent  # noqa: E402
import pricing  # noqa: E402
from detectors import workload_classifier  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(hours_offset: int = 0) -> datetime:
    """Return a UTC datetime spaced hours_offset hours from a fixed base."""
    base = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    return base + timedelta(hours=hours_offset)


def _turn(session_id="s1", is_sidechain=False, session_kind=None,
          model="claude-sonnet-4-6", timestamp=None):
    return Turn(
        uuid="u", message_id="m", request_id="r",
        session_id=session_id, cwd="/tmp/myproject",
        timestamp=timestamp,
        model=model,
        usage=Usage(input_tokens=100, output_tokens=50),
        is_sidechain=is_sidechain,
        session_kind=session_kind,
    )


def _session(session_id, cwd, turns, first_ts, last_ts, models_used=None):
    s = Session(session_id=session_id, cwd=cwd)
    s.turns = turns
    s.first_timestamp = first_ts
    s.last_timestamp = last_ts
    s.models_used = models_used or {"claude-sonnet-4-6": len(turns)}
    return s


def _bash_event(session_id, command_head):
    return CausalEvent(
        tool_use_id="tid", session_id=session_id,
        event_type="tool_result", tool_name="Bash",
        command_head=command_head,
    )


# ---------------------------------------------------------------------------
# Build a set of sessions spanning many days with low session rate
# ---------------------------------------------------------------------------

def _low_volume_sessions():
    """2 sessions over 2 days = 1 session/day — below threshold."""
    sessions = []
    for i in range(2):
        ts = _ts(hours_offset=i * 24)
        turns = [_turn(session_id=f"s{i}", timestamp=ts)]
        sessions.append(_session(
            session_id=f"s{i}",
            cwd="/tmp/myproject",
            turns=turns,
            first_ts=ts,
            last_ts=ts,
        ))
    return sessions


def _high_volume_sessions(n=15, interval_hours=None, cwd="/tmp/myproject",
                          session_kind=None, is_sidechain=False):
    """n sessions over 1 day = n sessions/day — above threshold."""
    sessions = []
    for i in range(n):
        if interval_hours is not None:
            ts = _ts(hours_offset=i * interval_hours)
        else:
            # Spread across ~24 hours with varied intervals
            ts = _ts(hours_offset=i * 1.5)
        turns = [_turn(
            session_id=f"s{i}",
            timestamp=ts,
            is_sidechain=is_sidechain,
            session_kind=session_kind,
        )]
        sessions.append(_session(
            session_id=f"s{i}",
            cwd=cwd,
            turns=turns,
            first_ts=ts,
            last_ts=ts,
        ))
    return sessions


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWorkloadClassifier(unittest.TestCase):

    # 1. Low volume → no leak
    def test_no_flag_low_volume_project(self):
        sessions = _low_volume_sessions()
        leaks = workload_classifier.detect(sessions, [], None, pricing)
        self.assertEqual(leaks, [])

    # 2. High volume with only 2-3 automation signals → high_volume_parallel_workload
    def test_high_volume_classified_as_parallel_workload(self):
        # 15 sessions / ~1 day, varied intervals, only "same cwd" + possibly off-hours
        # signals — not all 5 → should be parallel_workload, not automation
        sessions = _high_volume_sessions(n=15, interval_hours=None)
        leaks = workload_classifier.detect(sessions, [], None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "workload:high_volume_parallel_workload")

    # 3. 4 out of 5 signals still → high_volume_parallel_workload
    def test_automation_requires_all_5_signals(self):
        # 15 sessions with stable interval (1 hr) and same cwd and repeated command
        # but NOT off-hours (10:00 UTC) and NOT low interactive — only 3-4 signals
        sessions = _high_volume_sessions(n=15, interval_hours=1)
        # Repeated bash command for each session
        causal_events = [_bash_event(f"s{i}", "pytest tests/") for i in range(15)]
        leaks = workload_classifier.detect(sessions, causal_events, None, pricing)
        self.assertEqual(len(leaks), 1)
        # With only 3-4 signals, should be parallel workload not automation
        # (off-hours signal will be False since hours are 10:00–24:00 UTC;
        # interactive share signal depends on session_kind — all default None = interactive)
        ids = [leak.id for leak in leaks]
        self.assertIn("workload:high_volume_parallel_workload", ids)
        self.assertNotIn("workload:possible_recurring_automation", ids)

    # 4. All 5 signals present → possible_recurring_automation
    def test_possible_automation_emitted_on_all_signals(self):
        # Build sessions that trigger all 5 signals:
        # 1. Stable interval: exactly 1 hour apart (falls in 1-hr bucket)
        # 2. Repeated command: all use "pytest"
        # 3. Single cwd: all same
        # 4. Off-hours: start at 23:00 UTC (off-hours)
        # 5. Little interactive: all session_kind="bg"
        # Use 11 sessions spaced 1 hour apart → 11/((11-1)/24) ≈ 26.4 sessions/day > 10
        n = 11
        sessions = []
        for i in range(n):
            ts = datetime(2026, 6, 1, 23, 0, tzinfo=timezone.utc) + timedelta(hours=i)
            turns = [_turn(
                session_id=f"s{i}",
                timestamp=ts,
                is_sidechain=False,
                session_kind="bg",  # not interactive
            )]
            sessions.append(_session(
                session_id=f"s{i}",
                cwd="/tmp/myproject",
                turns=turns,
                first_ts=ts,
                last_ts=ts,
            ))
        causal_events = [_bash_event(f"s{i}", "pytest tests/") for i in range(n)]
        leaks = workload_classifier.detect(sessions, causal_events, None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "workload:possible_recurring_automation")
        self.assertEqual(leaks[0].severity, "warning")

    # 5. Basis fields on emitted leak
    def test_workload_leak_has_correct_basis_fields(self):
        sessions = _high_volume_sessions(n=15)
        leaks = workload_classifier.detect(sessions, [], None, pricing)
        self.assertEqual(len(leaks), 1)
        leak = leaks[0]
        self.assertEqual(leak.basis, "workload")
        self.assertEqual(leak.overlap_group, "workload_classification")
        self.assertFalse(leak.additive)
        self.assertEqual(leak.est_weekly_savings_usd, 0.0)

    # 6. Empty sessions list → no crash, returns []
    def test_no_sessions_no_crash(self):
        leaks = workload_classifier.detect([], [], None, pricing)
        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
