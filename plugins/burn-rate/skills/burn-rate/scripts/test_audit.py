# test_audit.py
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import audit  # noqa: E402
import jsonl_parser as jp  # noqa: E402


def _empty_stats():
    return jp.ParseStats()


class TestAudit(unittest.TestCase):
    def test_run_audit_shape(self):
        with mock.patch("audit.jsonl_parser.parse_all", return_value=([], [], _empty_stats(), [])), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "ccusage skipped")), \
             mock.patch("audit.config_inspector.build_snapshot",
                        return_value=mock.Mock(tool_search_enabled=True, tool_search_mode="default",
                                               hooks=[], mcp_servers=[], plugins=[], skill_count=0,
                                               claude_md_tokens={})):
            result = audit.run_audit(days=7)
        for key in ("summary", "ccusage_error", "parser_errors", "bottlenecks",
                    "leaks", "total_weekly_savings_usd", "detector_errors"):
            self.assertIn(key, result)
        # Must be JSON-serializable
        json.dumps(result, default=str)

    def test_parser_errors_surface_in_output(self):
        errors = ["foo.jsonl: 3 unparseable line(s)", "bar.jsonl: PermissionError"]
        with mock.patch("audit.jsonl_parser.parse_all", return_value=([], [], _empty_stats(), errors)), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "ccusage skipped")), \
             mock.patch("audit.config_inspector.build_snapshot",
                        return_value=mock.Mock(tool_search_enabled=True, tool_search_mode="default",
                                               hooks=[], mcp_servers=[], plugins=[], skill_count=0,
                                               claude_md_tokens={})):
            result = audit.run_audit(days=7)
        self.assertEqual(result["parser_errors"], errors)


if __name__ == "__main__":
    unittest.main()
