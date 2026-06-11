# test_config_inspector.py
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import config_inspector as ci  # noqa: E402


class TestConfigInspector(unittest.TestCase):
    def test_tool_search_default_on(self):
        self.assertEqual(ci.detect_tool_search({}, {}), (True, "default"))

    def test_tool_search_explicit_off(self):
        self.assertEqual(ci.detect_tool_search({"ENABLE_TOOL_SEARCH": "false"}, {}),
                         (False, "false"))

    def test_count_hooks(self):
        settings = {"hooks": {"SessionStart": [{"hooks": [{"command": "x"}, {"command": "y"}]}]}}
        self.assertEqual(len(ci.read_hooks(settings, "global")), 2)

    def test_read_hooks_skips_malformed(self):
        # Malformed user settings.json: a non-dict group and a non-dict hook must be
        # skipped defensively rather than raising AttributeError and breaking the audit.
        settings = {"hooks": {"SessionStart": ["bad-group", {"hooks": ["bad-hook", {"command": "ok"}]}]}}
        result = ci.read_hooks(settings, "global")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["command"], "ok")

    def test_claude_md_size(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "CLAUDE.md"
            p.write_text("x" * 8000, encoding="utf-8")
            self.assertEqual(ci.approx_tokens(p), 2000)  # bytes // 4


if __name__ == "__main__":
    unittest.main()
