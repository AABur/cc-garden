# test_cache.py
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import Turn, Usage, Session  # noqa: E402
import pricing  # noqa: E402
from detectors import cache  # noqa: E402


def _turn(inp, cr):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=None, model="claude-opus-4-8",
                usage=Usage(input_tokens=inp, cache_read_tokens=cr))


def _ts_turn(ts, cw=0, inp=0, cr=0, out=0):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=ts, model="claude-opus-4-8",
                usage=Usage(input_tokens=inp, output_tokens=out, cache_read_tokens=cr,
                            cache_write_5m_tokens=cw))


class TestCache(unittest.TestCase):
    def _sess(self, turns, sid="s"):
        s = Session(session_id=sid, cwd="/tmp/p")
        s.turns = turns
        return s

    def test_flags_low_hit_with_big_input(self):
        # 600k input, only 100k cache read -> hit ratio ~0.14, prefix >> 4096
        turns = [_turn(600_000, 100_000)]
        leaks = cache.detect([self._sess(turns)], [], None, pricing)
        self.assertEqual(len(leaks), 1)

    def test_no_flag_when_healthy(self):
        turns = [_turn(50_000, 900_000)]  # ~0.95 hit ratio
        self.assertEqual(cache.detect([self._sess(turns)], [], None, pricing), [])

    def test_no_flag_when_input_tiny(self):
        turns = [_turn(2000, 0)]  # denom 2000 < MIN_INPUT -> skipped by the first guard
        self.assertEqual(cache.detect([self._sess(turns)], [], None, pricing), [])

    def test_no_flag_many_tiny_input_turns(self):
        # 600 turns x 1000 input, 0 cache read -> denom 600k >= MIN_INPUT and ratio 0,
        # but avg input/turn (1000) < opus cacheable min (4096) -> not user's fault, skip.
        turns = [_turn(1000, 0) for _ in range(600)]
        self.assertEqual(cache.detect([self._sess(turns)], [], None, pricing), [])


    # --- prefix_rewrite_after_pause signal -------------------------------

    def _pause_rewrite_session(self, sid):
        # Two turns >5 min apart, second has a large cache-write (50k) -> one event.
        base = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
        t1 = _ts_turn(base, cw=1000, inp=1000)
        t2 = _ts_turn(base + timedelta(minutes=6), cw=60_000, inp=1000)
        return self._sess([t1, t2], sid=sid)

    def test_prefix_rewrite_flag_emitted(self):
        sessions = [self._pause_rewrite_session(f"sess{i}") for i in range(3)]
        leaks = cache.detect(sessions, [], None, pricing)
        rw = [l for l in leaks if l.id == "cache:prefix_rewrite_after_pause"]
        self.assertEqual(len(rw), 1)
        leak = rw[0]
        self.assertEqual(leak.basis, "spend")
        self.assertEqual(leak.severity, "warning")
        self.assertEqual(leak.overlap_group, "cache_efficiency")
        self.assertTrue(any("Peak day" in b for b in leak.evidence))

    def test_prefix_rewrite_est_weekly_tokens_is_observed_sum(self):
        sessions = [self._pause_rewrite_session(f"sess{i}") for i in range(3)]
        leaks = cache.detect(sessions, [], None, pricing)
        rw = next(l for l in leaks if l.id == "cache:prefix_rewrite_after_pause")
        # 3 events x 60_000 rewrite tokens = 180_000 (observed, not inflated)
        self.assertEqual(rw.est_weekly_tokens, 180_000)

    def test_no_prefix_rewrite_when_gap_short(self):
        base = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
        sessions = []
        for i in range(3):
            t1 = _ts_turn(base, cw=1000, inp=1000)
            t2 = _ts_turn(base + timedelta(minutes=2), cw=60_000, inp=1000)  # <5min
            sessions.append(self._sess([t1, t2], sid=f"sess{i}"))
        leaks = cache.detect(sessions, [], None, pricing)
        self.assertEqual([l for l in leaks if l.id == "cache:prefix_rewrite_after_pause"], [])

    def test_no_prefix_rewrite_below_min_rewrites(self):
        # Only 2 events < MIN_REWRITES=3
        sessions = [self._pause_rewrite_session(f"sess{i}") for i in range(2)]
        leaks = cache.detect(sessions, [], None, pricing)
        self.assertEqual([l for l in leaks if l.id == "cache:prefix_rewrite_after_pause"], [])

    def test_prefix_rewrite_exactly_300s_does_not_fire(self):
        # Strict > 300: a gap of exactly 300s must NOT trigger the leak.
        base = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
        sessions = []
        for i in range(3):
            t1 = _ts_turn(base, cw=1000, inp=1000)
            t2 = _ts_turn(base + timedelta(seconds=300), cw=60_000, inp=1000)
            sessions.append(self._sess([t1, t2], sid=f"sess{i}"))
        leaks = cache.detect(sessions, [], None, pricing)
        self.assertEqual([l for l in leaks if l.id == "cache:prefix_rewrite_after_pause"], [])

    def test_prefix_rewrite_301s_does_fire(self):
        # 301s > 300: should trigger once MIN_REWRITES is met.
        base = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
        sessions = []
        for i in range(3):
            t1 = _ts_turn(base, cw=1000, inp=1000)
            t2 = _ts_turn(base + timedelta(seconds=301), cw=60_000, inp=1000)
            sessions.append(self._sess([t1, t2], sid=f"sess{i}"))
        leaks = cache.detect(sessions, [], None, pricing)
        rw = [l for l in leaks if l.id == "cache:prefix_rewrite_after_pause"]
        self.assertEqual(len(rw), 1)

    def test_low_hit_ratio_does_not_spawn_prefix_rewrite(self):
        # Existing-style low-ratio fixture yields exactly low_hit_ratio, no rewrite leak.
        turns = [_turn(600_000, 100_000)]
        leaks = cache.detect([self._sess(turns)], [], None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "cache:low_hit_ratio")


if __name__ == "__main__":
    unittest.main()
