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
from detectors import Leak  # noqa: E402


def _empty_stats():
    return jp.ParseStats()


def _make_leak(id_, cost_usd, savings_usd):
    return Leak(
        id=id_,
        title=f"Leak {id_}",
        severity="warning",
        category="test",
        est_weekly_cost_usd=cost_usd,
        est_weekly_savings_usd=savings_usd,
    )


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
                    "leaks", "opportunity_ranking", "total_savings", "detector_errors"):
            self.assertIn(key, result)
        self.assertNotIn("total_weekly_savings_usd", result)
        self.assertIsInstance(result["opportunity_ranking"], list)
        self.assertEqual(result["total_savings"]["status"], "not_reported")
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

    def test_opportunity_ranking_sorted_by_cost(self):
        leak_a = _make_leak("detector:a", cost_usd=5.0, savings_usd=1.0)
        leak_b = _make_leak("detector:b", cost_usd=20.0, savings_usd=3.0)
        with mock.patch("audit.jsonl_parser.parse_all", return_value=([], [], _empty_stats(), [])), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "ccusage skipped")), \
             mock.patch("audit.config_inspector.build_snapshot",
                        return_value=mock.Mock(tool_search_enabled=True, tool_search_mode="default",
                                               hooks=[], mcp_servers=[], plugins=[], skill_count=0,
                                               claude_md_tokens={})), \
             mock.patch("audit._DETECTOR_MODULES", [mock.Mock(detect=lambda *_: [leak_a, leak_b])]):
            result = audit.run_audit(days=7)
        ranking = result["opportunity_ranking"]
        self.assertEqual(len(ranking), 2)
        # Sorted descending by rank_signal_cost_usd
        self.assertGreaterEqual(
            ranking[0]["rank_signal_cost_usd"],
            ranking[1]["rank_signal_cost_usd"],
        )
        self.assertEqual(ranking[0]["id"], "detector:b")
        self.assertEqual(ranking[1]["id"], "detector:a")
        # Each entry has the required fields
        for entry in ranking:
            for f in ("id", "rank_signal_tokens", "rank_signal_cost_usd", "additive", "overlap_group"):
                self.assertIn(f, entry)


if __name__ == "__main__":
    unittest.main()
