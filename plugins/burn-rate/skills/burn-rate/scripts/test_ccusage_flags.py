# test_ccusage_flags.py
"""Tests for ccusage binary detection, timeout parameter, and audit --skip-ccusage flag."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ccusage  # noqa: E402
import audit  # noqa: E402
import jsonl_parser as jp  # noqa: E402


def _empty_parse():
    return ([], [], jp.ParseStats(), [])


def _mock_config():
    return mock.Mock(
        tool_search_enabled=True,
        tool_search_mode="default",
        hooks=[],
        mcp_servers=[],
        plugins=[],
        skill_count=0,
        claude_md_tokens={},
    )


class TestCcusageBinaryDetection(unittest.TestCase):
    def test_run_daily_uses_installed_binary_when_available(self):
        """When ccusage is on PATH, _run should call it directly, not via npx."""
        fake_json = json.dumps({"daily": [{"date": "2026-06-10", "totalCost": 0.5}]})
        fake_result = mock.Mock(returncode=0, stdout=fake_json, stderr="")
        with mock.patch("ccusage.shutil.which", return_value="/usr/local/bin/ccusage"), \
             mock.patch("ccusage.subprocess.run", return_value=fake_result) as mock_run:
            data, err = ccusage.run_daily(days=7)
        self.assertIsNone(err)
        self.assertIsNotNone(data)
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "ccusage", f"Expected 'ccusage' binary, got: {cmd[0]}")

    def test_run_daily_falls_back_to_npx_when_not_installed(self):
        """When ccusage is not on PATH, _run should fall back to npx."""
        fake_json = json.dumps({"daily": []})
        fake_result = mock.Mock(returncode=0, stdout=fake_json, stderr="")
        with mock.patch("ccusage.shutil.which", return_value=None), \
             mock.patch("ccusage.subprocess.run", return_value=fake_result) as mock_run:
            data, err = ccusage.run_daily(days=7)
        self.assertIsNone(err)
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "npx", f"Expected 'npx' fallback, got: {cmd[0]}")

    def test_run_daily_respects_timeout_parameter(self):
        """run_daily(timeout=10) must pass timeout=10 down to subprocess.run."""
        fake_json = json.dumps({"daily": []})
        fake_result = mock.Mock(returncode=0, stdout=fake_json, stderr="")
        with mock.patch("ccusage.shutil.which", return_value=None), \
             mock.patch("ccusage.subprocess.run", return_value=fake_result) as mock_run:
            ccusage.run_daily(days=7, timeout=10)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 10)


class TestAuditSkipCcusageFlag(unittest.TestCase):
    def test_audit_skip_ccusage_flag(self):
        """When --skip-ccusage is set, ccusage.run_daily must not be called."""
        with mock.patch("audit.jsonl_parser.parse_all", return_value=_empty_parse()), \
             mock.patch("audit.ccusage.run_daily") as mock_ccusage, \
             mock.patch("audit.config_inspector.build_snapshot", return_value=_mock_config()):
            result = audit.run_audit(days=7, skip_ccusage=True)
        mock_ccusage.assert_not_called()
        self.assertIsNone(result["ccusage"])
        self.assertEqual(result["ccusage_error"], "skipped")
        self.assertEqual(result["reconciliation"]["status"], "skipped")

    def test_audit_reconciliation_block_present(self):
        """Output dict must always contain a 'reconciliation' key with a 'note' field."""
        with mock.patch("audit.jsonl_parser.parse_all", return_value=_empty_parse()), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "ccusage unavailable: test")), \
             mock.patch("audit.config_inspector.build_snapshot", return_value=_mock_config()):
            result = audit.run_audit(days=7)
        self.assertIn("reconciliation", result)
        self.assertIn("note", result["reconciliation"])
        self.assertIn("status", result["reconciliation"])
        self.assertEqual(result["reconciliation"]["status"], "failed")

    def test_audit_reconciliation_matched_when_ccusage_succeeds(self):
        """reconciliation.status == 'matched' when ccusage returns data without error."""
        fake_data = {"daily": [{"date": "2026-06-10", "totalCost": 1.0}]}
        with mock.patch("audit.jsonl_parser.parse_all", return_value=_empty_parse()), \
             mock.patch("audit.ccusage.run_daily", return_value=(fake_data, None)), \
             mock.patch("audit.config_inspector.build_snapshot", return_value=_mock_config()):
            result = audit.run_audit(days=7)
        self.assertEqual(result["reconciliation"]["status"], "matched")

    def test_audit_ccusage_timeout_forwarded(self):
        """ccusage_timeout kwarg in run_audit is forwarded to ccusage.run_daily."""
        with mock.patch("audit.jsonl_parser.parse_all", return_value=_empty_parse()), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "unavailable")) as mock_ccusage, \
             mock.patch("audit.config_inspector.build_snapshot", return_value=_mock_config()):
            audit.run_audit(days=7, ccusage_timeout=10)
        mock_ccusage.assert_called_once_with(days=7, timeout=10)


if __name__ == "__main__":
    unittest.main()
