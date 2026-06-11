# test_audit.py
import json
import unittest
from unittest import mock
import audit


class TestAudit(unittest.TestCase):
    def test_run_audit_shape(self):
        with mock.patch("audit.jsonl_parser.parse_all", return_value=[]), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "ccusage skipped")), \
             mock.patch("audit.config_inspector.build_snapshot",
                        return_value=mock.Mock(tool_search_enabled=True, tool_search_mode="default",
                                               hooks=[], mcp_servers=[], plugins=[], skill_count=0,
                                               claude_md_tokens={})):
            result = audit.run_audit(days=7)
        for key in ("summary", "ccusage_error", "bottlenecks", "leaks",
                    "total_weekly_savings_usd", "detector_errors"):
            self.assertIn(key, result)
        # Must be JSON-serializable
        json.dumps(result, default=str)


if __name__ == "__main__":
    unittest.main()
