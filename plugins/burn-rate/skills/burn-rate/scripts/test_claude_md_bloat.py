# test_claude_md_bloat.py
import unittest
from jsonl_parser import Session
import pricing
from detectors import claude_md_bloat as cmb


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


if __name__ == "__main__":
    unittest.main()
