# test_attribution.py
import unittest
import attribution
from jsonl_parser import Turn, Usage, Session


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

    def test_workflow_vs_interactive(self):
        s = self._sess([_t(kind="bg", out=200), _t(kind=None, out=100)])
        res = attribution.by_dimension([s], "session_kind")
        self.assertEqual(res["bg"], 200)
        self.assertEqual(res["interactive"], 100)


if __name__ == "__main__":
    unittest.main()
