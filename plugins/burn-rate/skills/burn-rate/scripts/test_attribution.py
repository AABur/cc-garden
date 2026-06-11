# test_attribution.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import attribution  # noqa: E402
from jsonl_parser import Turn, Usage, Session  # noqa: E402


def _t(skill=None, plugin=None, agent=None, kind=None, out=100):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s",
                cwd="/tmp/p", timestamp=None, model="claude-opus-4-8",
                usage=Usage(output_tokens=out), session_kind=kind,
                attribution_skill=skill, attribution_plugin=plugin, attribution_agent=agent)


class TestAttribution(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p")
        s.turns = turns
        return s

    def test_groups_by_skill(self):
        s = self._sess([_t(skill="find-skills", out=100), _t(skill="find-skills", out=50),
                        _t(skill="retro", out=30)])
        res = attribution.by_dimension([s], "attribution_skill")
        self.assertEqual(res["find-skills"], 150)
        self.assertEqual(res["retro"], 30)

    def test_missing_skill_buckets_as_unknown(self):
        # Turns without attribution must still be counted, under '<unknown>',
        # so the Pareto totals don't silently omit a large share of tokens.
        s = self._sess([_t(skill="retro", out=30), _t(skill=None, out=70)])
        res = attribution.by_dimension([s], "attribution_skill")
        self.assertEqual(res["retro"], 30)
        self.assertEqual(res["<unknown>"], 70)

    def test_workflow_vs_interactive(self):
        s = self._sess([_t(kind="bg", out=200), _t(kind=None, out=100)])
        res = attribution.by_dimension([s], "session_kind")
        self.assertEqual(res["bg"], 200)
        self.assertEqual(res["interactive"], 100)

    def test_sums_all_token_buckets(self):
        t = Turn(uuid="u", message_id="m", request_id="r", session_id="s",
                 cwd="/tmp/p", timestamp=None, model="claude-opus-4-8",
                 usage=Usage(input_tokens=10, output_tokens=20, cache_read_tokens=30,
                             cache_write_5m_tokens=40, cache_write_1h_tokens=50),
                 attribution_skill="x")
        res = attribution.by_dimension([self._sess([t])], "attribution_skill")
        self.assertEqual(res["x"], 150)  # 10+20+30+40+50


if __name__ == "__main__":
    unittest.main()
