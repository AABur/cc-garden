# test_subagent_model_selection.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import Turn, Usage, Session  # noqa: E402
import pricing  # noqa: E402
from detectors import subagent_model_selection  # noqa: E402


def _opus(out, sidechain=False, kind=None):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=None, model="claude-opus-4-8",
                usage=Usage(input_tokens=5, output_tokens=out, cache_read_tokens=1000),
                is_sidechain=sidechain, session_kind=kind)


class TestSubagentModelSelection(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p")
        s.turns = turns
        return s

    def test_flags_short_opus_sidechain(self):
        """Sidechain turns with short Opus output should produce a leak."""
        turns = [_opus(50, sidechain=True) for _ in range(15)]
        leaks = subagent_model_selection.detect([self._sess(turns)], [], None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "model_routing:subagent_opus_simple")

    def test_flags_short_opus_bg(self):
        """Background (session_kind='bg') turns with short Opus output should produce a leak."""
        turns = [_opus(50, kind="bg") for _ in range(15)]
        leaks = subagent_model_selection.detect([self._sess(turns)], [], None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "model_routing:subagent_opus_simple")

    def test_excludes_interactive_turns(self):
        """Interactive (non-sidechain, non-bg) turns must NOT be flagged — that is model_selection.py's job."""
        turns = [_opus(50) for _ in range(40)]
        leaks = subagent_model_selection.detect([self._sess(turns)], [], None, pricing)
        self.assertEqual(leaks, [])

    def test_below_min_count_no_flag(self):
        """Fewer than MIN_TURNS (10) matching turns should produce no leak."""
        turns = [_opus(50, sidechain=True) for _ in range(5)]
        leaks = subagent_model_selection.detect([self._sess(turns)], [], None, pricing)
        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
