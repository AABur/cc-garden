# test_context_rot.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import Turn, Usage, Session  # noqa: E402
import pricing  # noqa: E402
from detectors import context_rot  # noqa: E402


def _turn(ctx):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=None, model="claude-opus-4-8",
                usage=Usage(cache_read_tokens=ctx))


class TestContextRot(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p")
        s.turns = turns
        return s

    def test_flags_when_enough_over_threshold(self):
        turns = [_turn(450_000) for _ in range(12)]
        leaks = context_rot.detect([self._sess(turns)], None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].category, "context")

    def test_no_flag_below_count(self):
        turns = [_turn(450_000) for _ in range(3)]
        self.assertEqual(context_rot.detect([self._sess(turns)], None, pricing), [])

    def test_no_flag_below_threshold(self):
        turns = [_turn(100_000) for _ in range(20)]
        self.assertEqual(context_rot.detect([self._sess(turns)], None, pricing), [])


if __name__ == "__main__":
    unittest.main()
