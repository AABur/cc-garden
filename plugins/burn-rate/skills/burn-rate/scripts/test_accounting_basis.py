# test_accounting_basis.py
"""Tests for ParseStats dataclass and accounting_basis audit output (Phase 2, Step 1)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jsonl_parser as jp  # noqa: E402
import audit  # noqa: E402


def _assistant_record(uuid, msg_id, req_id, sidechain=False):
    return {
        "type": "assistant", "uuid": uuid, "requestId": req_id,
        "sessionId": "s1", "cwd": "/tmp/proj",
        "timestamp": "2026-06-10T00:00:00Z",
        "isSidechain": sidechain,
        "message": {
            "id": msg_id, "model": "claude-opus-4-8", "role": "assistant",
            "content": [],
            "usage": {
                "input_tokens": 5, "output_tokens": 10,
                "cache_read_input_tokens": 0,
                "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0},
                "cache_creation_input_tokens": 0, "service_tier": "standard",
            },
        },
    }


def _user_record(uuid):
    return {
        "type": "user", "uuid": uuid,
        "sessionId": "s1", "cwd": "/tmp/proj",
        "timestamp": "2026-06-10T00:00:00Z",
        "message": {"role": "user", "content": []},
    }


class TestParseStatsCounts(unittest.TestCase):
    def test_parse_stats_counts_raw_assistant_records(self):
        # 3 assistant records: 2 unique (msg_id/req_id), 1 duplicate
        records = [
            _assistant_record("u1", "m1", "r1"),
            _assistant_record("u2", "m1", "r1"),  # duplicate of first
            _assistant_record("u3", "m2", "r2"),
        ]
        _sess, stats = jp.build_session_from_records("s1", records)
        self.assertEqual(stats.raw_assistant_records, 3)
        self.assertEqual(stats.deduped_assistant_requests, 2)
        self.assertEqual(stats.duplicates_removed, 1)

    def test_parse_stats_counts_sidechain(self):
        # 2 assistant records, 1 has isSidechain=True
        records = [
            _assistant_record("u1", "m1", "r1", sidechain=False),
            _assistant_record("u2", "m2", "r2", sidechain=True),
        ]
        _sess, stats = jp.build_session_from_records("s1", records)
        self.assertEqual(stats.sidechain_assistant_records, 1)

    def test_parse_stats_counts_user_tool_events(self):
        # Mix of assistant and user records
        records = [
            _assistant_record("u1", "m1", "r1"),
            _user_record("u2"),
            _user_record("u3"),
            _assistant_record("u4", "m2", "r2"),
        ]
        _sess, stats = jp.build_session_from_records("s1", records)
        self.assertEqual(stats.user_tool_events, 2)

    def test_parse_stats_total_is_assistant_plus_user(self):
        # total_parsed_events = raw_assistant_records + user_tool_events
        records = [
            _assistant_record("u1", "m1", "r1"),
            _assistant_record("u2", "m2", "r2"),
            _user_record("u3"),
        ]
        _sess, stats = jp.build_session_from_records("s1", records)
        self.assertEqual(
            stats.total_parsed_events,
            stats.raw_assistant_records + stats.user_tool_events,
        )

    def test_parse_stats_hook_events_zero(self):
        # hook_events is 0 in Phase 2 Step 1 (hook parsing comes in Step 3)
        records = [_assistant_record("u1", "m1", "r1")]
        _sess, stats = jp.build_session_from_records("s1", records)
        self.assertEqual(stats.hook_events, 0)


class TestParseSessionFileReturnsTuple(unittest.TestCase):
    def test_parse_session_file_returns_three_tuple(self):
        # parse_session_file must return (session, stats, bad_lines)
        import tempfile
        import json as _json
        record = _assistant_record("u1", "m1", "r1")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s1.jsonl"
            p.write_text(_json.dumps(record) + "\n", encoding="utf-8")
            result = jp.parse_session_file(p, since=None)
        self.assertEqual(len(result), 3, "parse_session_file must return a 3-tuple (session, stats, bad_lines)")
        sess, stats, bad_lines = result
        self.assertIsInstance(stats, jp.ParseStats)
        self.assertEqual(bad_lines, 0)


class TestParseAllReturnsFourTuple(unittest.TestCase):
    def test_parse_all_returns_four_tuple(self):
        # parse_all must return (sessions, causal_events, stats, errors)
        import tempfile
        import json as _json
        record = _assistant_record("u1", "m1", "r1")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s1.jsonl"
            p.write_text(_json.dumps(record) + "\n", encoding="utf-8")
            result = jp.parse_all(projects_dir=Path(d), since_days=30)
        self.assertEqual(len(result), 4, "parse_all must return a 4-tuple (sessions, causal_events, stats, errors)")
        sessions, causal_events, stats, errors = result
        self.assertIsInstance(stats, jp.ParseStats)
        self.assertIsInstance(causal_events, list)


class TestAuditAccountingBasis(unittest.TestCase):
    def _make_mock_stats(self):
        stats = jp.ParseStats(
            raw_assistant_records=10,
            deduped_assistant_requests=8,
            duplicates_removed=2,
            sidechain_assistant_records=1,
            user_tool_events=5,
            hook_events=0,
            total_parsed_events=15,
        )
        return stats

    def test_audit_output_has_accounting_basis(self):
        # run_audit() output must contain "accounting_basis" with correct primary key
        stats = self._make_mock_stats()
        with mock.patch("audit.jsonl_parser.parse_all", return_value=([], [], stats, [])), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "ccusage skipped")), \
             mock.patch("audit.config_inspector.build_snapshot",
                        return_value=mock.Mock(
                            tool_search_enabled=True, tool_search_mode="default",
                            hooks=[], mcp_servers=[], plugins=[], skill_count=0,
                            claude_md_tokens={})):
            result = audit.run_audit(days=7)
        self.assertIn("accounting_basis", result)
        self.assertEqual(result["accounting_basis"]["primary"], "local_deduped_transcript_usage")

    def test_audit_accounting_basis_fields(self):
        # accounting_basis must include all expected stats fields
        stats = self._make_mock_stats()
        with mock.patch("audit.jsonl_parser.parse_all", return_value=([], [], stats, [])), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "ccusage skipped")), \
             mock.patch("audit.config_inspector.build_snapshot",
                        return_value=mock.Mock(
                            tool_search_enabled=True, tool_search_mode="default",
                            hooks=[], mcp_servers=[], plugins=[], skill_count=0,
                            claude_md_tokens={})):
            result = audit.run_audit(days=7)
        ab = result["accounting_basis"]
        for field in ("raw_assistant_records", "deduped_assistant_requests",
                      "duplicates_removed", "sidechain_records",
                      "user_tool_events", "hook_events", "total_parsed_events", "note"):
            self.assertIn(field, ab, f"missing field: {field}")
        self.assertEqual(ab["raw_assistant_records"], 10)
        self.assertEqual(ab["deduped_assistant_requests"], 8)
        self.assertEqual(ab["duplicates_removed"], 2)


if __name__ == "__main__":
    unittest.main()
