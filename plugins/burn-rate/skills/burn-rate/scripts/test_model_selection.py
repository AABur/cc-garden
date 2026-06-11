# test_model_selection.py
import unittest
from jsonl_parser import Turn, Usage, Session
import pricing
from detectors import model_selection


def _opus(out, sidechain=False, kind=None):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=None, model="claude-opus-4-8",
                usage=Usage(input_tokens=5, output_tokens=out, cache_read_tokens=1000),
                is_sidechain=sidechain, session_kind=kind)


class TestModelSelection(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p"); s.turns = turns; return s

    def test_flags_interactive_simple_opus(self):
        turns = [_opus(50) for _ in range(40)]
        leaks = model_selection.detect([self._sess(turns)], None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertIn("40", leaks[0].title)

    def test_excludes_sidechain_and_bg(self):
        turns = [_opus(50, sidechain=True) for _ in range(40)] + [_opus(50, kind="bg") for _ in range(40)]
        leaks = model_selection.detect([self._sess(turns)], None, pricing)
        self.assertEqual(leaks, [])

    def test_below_min_count_no_flag(self):
        turns = [_opus(50) for _ in range(5)]
        self.assertEqual(model_selection.detect([self._sess(turns)], None, pricing), [])


if __name__ == "__main__":
    unittest.main()
