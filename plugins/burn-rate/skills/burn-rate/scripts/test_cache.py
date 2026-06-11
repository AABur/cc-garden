# test_cache.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import Turn, Usage, Session
import pricing
from detectors import cache


def _turn(inp, cr):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=None, model="claude-opus-4-8",
                usage=Usage(input_tokens=inp, cache_read_tokens=cr))


class TestCache(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p"); s.turns = turns; return s

    def test_flags_low_hit_with_big_input(self):
        # 600k input, only 100k cache read -> hit ratio ~0.14, prefix >> 4096
        turns = [_turn(600_000, 100_000)]
        leaks = cache.detect([self._sess(turns)], None, pricing)
        self.assertEqual(len(leaks), 1)

    def test_no_flag_when_healthy(self):
        turns = [_turn(50_000, 900_000)]  # ~0.95 hit ratio
        self.assertEqual(cache.detect([self._sess(turns)], None, pricing), [])

    def test_no_flag_when_input_tiny(self):
        turns = [_turn(2000, 0)]  # denom 2000 < MIN_INPUT -> skipped by the first guard
        self.assertEqual(cache.detect([self._sess(turns)], None, pricing), [])

    def test_no_flag_many_tiny_input_turns(self):
        # 600 turns x 1000 input, 0 cache read -> denom 600k >= MIN_INPUT and ratio 0,
        # but avg input/turn (1000) < opus cacheable min (4096) -> not user's fault, skip.
        turns = [_turn(1000, 0) for _ in range(600)]
        self.assertEqual(cache.detect([self._sess(turns)], None, pricing), [])


if __name__ == "__main__":
    unittest.main()
