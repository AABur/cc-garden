# test_claude_md_bloat.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import Session  # noqa: E402
import pricing  # noqa: E402
from detectors import claude_md_bloat as cmb  # noqa: E402


class FakeConfig:
    def __init__(self, tokens):
        self.claude_md_tokens = tokens


class TestClaudeMdBloat(unittest.TestCase):
    def test_flags_oversized(self):
        cfg = FakeConfig({"/home/u/.claude/CLAUDE.md": 5000})
        leaks = cmb.detect([Session(session_id="s")], cfg, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].severity, "warning")

    def test_no_flag_within_target(self):
        cfg = FakeConfig({"/home/u/.claude/CLAUDE.md": 1500})
        self.assertEqual(cmb.detect([Session(session_id="s")], cfg, pricing), [])

    def test_critical_above_critical_threshold(self):
        cfg = FakeConfig({"/home/u/.claude/CLAUDE.md": 6000})
        leaks = cmb.detect([Session(session_id="s")], cfg, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].severity, "critical")

    def test_boundary_at_target_not_flagged(self):
        # Exactly TARGET tokens is within budget (the guard is `<= TARGET`).
        cfg = FakeConfig({"/home/u/.claude/CLAUDE.md": cmb.TARGET})
        self.assertEqual(cmb.detect([Session(session_id="s")], cfg, pricing), [])


if __name__ == "__main__":
    unittest.main()
