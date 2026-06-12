# test_causal_parser.py
"""Tests for CausalEvent extraction from JSONL assistant/user records."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jsonl_parser as jp  # noqa: E402


def _make_assistant_with_tool_use(tool_use_id, tool_name, tool_input,
                                   session_id="s1"):
    """Build a minimal assistant record containing one tool_use block."""
    return {
        "type": "assistant",
        "uuid": "u1",
        "requestId": "r1",
        "sessionId": session_id,
        "cwd": "/tmp/proj",
        "timestamp": "2026-06-10T00:00:00Z",
        "isSidechain": False,
        "message": {
            "id": "m1",
            "model": "claude-opus-4-8",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": tool_name,
                    "input": tool_input,
                }
            ],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read_input_tokens": 0,
                "cache_creation": {
                    "ephemeral_5m_input_tokens": 0,
                    "ephemeral_1h_input_tokens": 0,
                },
                "cache_creation_input_tokens": 0,
            },
        },
    }


def _make_user_with_tool_result(tool_use_id, content, is_error=False,
                                 session_id="s1"):
    """Build a minimal user record containing one tool_result block."""
    return {
        "type": "user",
        "uuid": "u2",
        "sessionId": session_id,
        "cwd": "/tmp/proj",
        "timestamp": "2026-06-10T00:00:01Z",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": content,
                    "is_error": is_error,
                }
            ],
        },
    }


def _make_hook_attachment(hook_name, hook_event, content,
                          attachment_type="hook_success", exit_code=0,
                          session_id="s1"):
    """Build a minimal attachment record carrying a hook injection."""
    return {
        "type": "attachment",
        "isSidechain": False,
        "sessionId": session_id,
        "timestamp": "2026-06-10T00:00:02Z",
        "attachment": {
            "type": attachment_type,
            "hookName": hook_name,
            "hookEvent": hook_event,
            "toolUseID": "hook_tuid_1",
            "content": content,
            "stdout": "",
            "stderr": "",
            "exitCode": exit_code,
            "command": "bash /tmp/hook.sh",
            "durationMs": 49,
        },
    }


class TestHookAttachmentExtraction(unittest.TestCase):

    def test_hook_success_produces_one_event(self):
        """A hook_success attachment yields one CausalEvent of type 'hook'."""
        content = "=== HANDOFF ===\ncontext"
        records = [
            _make_hook_attachment("SessionStart:clear", "SessionStart", content)
        ]
        _sess, causal_events, _stats = jp.build_session_from_records("s1", records)
        self.assertEqual(len(causal_events), 1)
        evt = causal_events[0]
        self.assertEqual(evt.event_type, "hook")
        self.assertEqual(evt.hook_name, "SessionStart:clear")
        self.assertEqual(evt.hook_event, "SessionStart")
        self.assertEqual(evt.content_size, len(content))

    def test_hook_events_stat_incremented(self):
        """stats.hook_events counts hook attachments."""
        records = [
            _make_hook_attachment("A:b", "A", "x"),
            _make_hook_attachment("C:d", "C", "yy"),
        ]
        _sess, _causal_events, stats = jp.build_session_from_records("s1", records)
        self.assertEqual(stats.hook_events, 2)

    def test_content_size_falls_back_to_stdout(self):
        """content_size uses stdout length when content is empty/missing."""
        rec = _make_hook_attachment("A:b", "A", "")
        rec["attachment"]["content"] = ""
        rec["attachment"]["stdout"] = "stdout-bytes"
        _sess, causal_events, _stats = jp.build_session_from_records("s1", [rec])
        self.assertEqual(len(causal_events), 1)
        self.assertEqual(causal_events[0].content_size, len("stdout-bytes"))

    def test_is_error_for_hook_error_and_nonzero_exit(self):
        """is_error is True for hook_error type and for non-zero exitCode."""
        err_type = _make_hook_attachment(
            "A:b", "A", "boom", attachment_type="hook_error"
        )
        err_exit = _make_hook_attachment(
            "C:d", "C", "boom", attachment_type="hook_success", exit_code=2
        )
        clean = _make_hook_attachment("E:f", "E", "ok")
        _s1, ev_err_type, _t1 = jp.build_session_from_records("s1", [err_type])
        _s2, ev_err_exit, _t2 = jp.build_session_from_records("s1", [err_exit])
        _s3, ev_clean, _t3 = jp.build_session_from_records("s1", [clean])
        self.assertTrue(ev_err_type[0].is_error)
        self.assertTrue(ev_err_exit[0].is_error)
        self.assertFalse(ev_clean[0].is_error)

    def test_exit_code_string_falls_back_to_zero(self):
        """exitCode='error' (non-numeric string) must not raise; is_error stays False."""
        rec = _make_hook_attachment(
            "A:b", "A", "output", attachment_type="hook_success", exit_code="error"
        )
        # Must not raise
        _sess, causal_events, _stats = jp.build_session_from_records("s1", [rec])
        # Event is still emitted (session not dropped)
        self.assertEqual(len(causal_events), 1)
        # exitCode fell back to 0, type is hook_success -> is_error is False
        self.assertFalse(causal_events[0].is_error)

    def test_non_hook_attachment_ignored(self):
        """An attachment whose type is not hook_* is ignored entirely."""
        rec = _make_hook_attachment(
            "A:b", "A", "data", attachment_type="image"
        )
        _sess, causal_events, stats = jp.build_session_from_records("s1", [rec])
        self.assertEqual(len(causal_events), 0)
        self.assertEqual(stats.hook_events, 0)

    def test_hook_event_does_not_store_raw_content(self):
        """The hook CausalEvent stores only a size, never the raw content."""
        long_content = "SECRET-" + ("Z" * 500)
        records = [
            _make_hook_attachment("A:b", "A", long_content)
        ]
        _sess, causal_events, _stats = jp.build_session_from_records("s1", records)
        evt = causal_events[0]
        self.assertEqual(evt.command_head, "")
        self.assertEqual(evt.file_path, "")
        for value in vars(evt).values():
            self.assertNotEqual(value, long_content)

    def test_parse_all_includes_hook_events(self):
        """parse_all() surfaces hook causal events and aggregates the stat."""
        assistant_rec = {
            "type": "assistant",
            "uuid": "u99",
            "requestId": "r99",
            "sessionId": "s1",
            "cwd": "/tmp/proj",
            "timestamp": "2026-06-10T00:00:00Z",
            "isSidechain": False,
            "message": {
                "id": "m99",
                "model": "claude-opus-4-8",
                "role": "assistant",
                "content": [],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "cache_read_input_tokens": 0,
                    "cache_creation": {
                        "ephemeral_5m_input_tokens": 0,
                        "ephemeral_1h_input_tokens": 0,
                    },
                    "cache_creation_input_tokens": 0,
                },
            },
        }
        hook_rec = _make_hook_attachment(
            "SessionStart:clear", "SessionStart", "=== HANDOFF ==="
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s1.jsonl"
            lines = [json.dumps(assistant_rec), json.dumps(hook_rec)]
            p.write_text("\n".join(lines), encoding="utf-8")
            _sessions, causal_events, stats, _errors = jp.parse_all(
                projects_dir=Path(d), since_days=30
            )
        hook_evts = [e for e in causal_events if e.event_type == "hook"]
        self.assertEqual(len(hook_evts), 1)
        self.assertGreaterEqual(stats.hook_events, 1)


class TestCausalEventExtraction(unittest.TestCase):

    def test_bash_command_head_extracted(self):
        """command_head holds first 80 chars of a Bash tool_use command."""
        cmd = "cat /very/long/path/to/file"
        records = [
            _make_assistant_with_tool_use(
                "toolu_bash1", "Bash", {"command": cmd}
            ),
            _make_user_with_tool_result("toolu_bash1", "file contents"),
        ]
        _sess, causal_events, _stats = jp.build_session_from_records("s1", records)
        self.assertEqual(len(causal_events), 1)
        self.assertEqual(causal_events[0].command_head, cmd[:80])

    def test_command_head_truncated_at_80(self):
        """command_head is truncated to exactly 80 chars for long commands."""
        cmd = "A" * 120
        records = [
            _make_assistant_with_tool_use(
                "toolu_long", "Bash", {"command": cmd}
            ),
            _make_user_with_tool_result("toolu_long", "ok"),
        ]
        _sess, causal_events, _stats = jp.build_session_from_records("s1", records)
        self.assertEqual(len(causal_events), 1)
        self.assertEqual(len(causal_events[0].command_head), 80)
        self.assertEqual(causal_events[0].command_head, cmd[:80])

    def test_read_file_path_extracted(self):
        """file_path is populated for a Read tool_use block."""
        records = [
            _make_assistant_with_tool_use(
                "toolu_read1", "Read", {"file_path": "/home/user/foo.py"}
            ),
            _make_user_with_tool_result("toolu_read1", "file contents"),
        ]
        _sess, causal_events, _stats = jp.build_session_from_records("s1", records)
        self.assertEqual(len(causal_events), 1)
        self.assertEqual(causal_events[0].file_path, "/home/user/foo.py")

    def test_tool_result_content_size(self):
        """content_size equals len(str(content)) of the tool_result content."""
        content = "hello world"
        records = [
            _make_assistant_with_tool_use(
                "toolu_cs1", "Bash", {"command": "echo hello"}
            ),
            _make_user_with_tool_result("toolu_cs1", content),
        ]
        _sess, causal_events, _stats = jp.build_session_from_records("s1", records)
        self.assertEqual(len(causal_events), 1)
        self.assertEqual(causal_events[0].content_size, len(str(content)))

    def test_tool_result_linked_to_tool_use(self):
        """CausalEvent links tool_name from assistant record and content_size
        from user record when both share the same tool_use_id."""
        records = [
            _make_assistant_with_tool_use(
                "toolu_link1", "Bash", {"command": "ls"}
            ),
            _make_user_with_tool_result("toolu_link1", "file1\nfile2"),
        ]
        _sess, causal_events, _stats = jp.build_session_from_records("s1", records)
        self.assertEqual(len(causal_events), 1)
        evt = causal_events[0]
        self.assertEqual(evt.tool_name, "Bash")
        self.assertGreater(evt.content_size, 0)

    def test_parse_all_returns_causal_events(self):
        """parse_all() second element is a non-empty list of CausalEvent objects."""
        assistant_rec = _make_assistant_with_tool_use(
            "toolu_pa1", "Read", {"file_path": "/tmp/x.py"}
        )
        user_rec = _make_user_with_tool_result("toolu_pa1", "# code")
        # parse_all requires at least one assistant turn to keep the session
        # We include a second assistant record so the session has turns
        full_assistant = {
            "type": "assistant",
            "uuid": "u99",
            "requestId": "r99",
            "sessionId": "s1",
            "cwd": "/tmp/proj",
            "timestamp": "2026-06-10T00:00:00Z",
            "isSidechain": False,
            "message": {
                "id": "m99",
                "model": "claude-opus-4-8",
                "role": "assistant",
                "content": [],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "cache_read_input_tokens": 0,
                    "cache_creation": {
                        "ephemeral_5m_input_tokens": 0,
                        "ephemeral_1h_input_tokens": 0,
                    },
                    "cache_creation_input_tokens": 0,
                },
            },
        }
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s1.jsonl"
            lines = [
                json.dumps(full_assistant),
                json.dumps(assistant_rec),
                json.dumps(user_rec),
            ]
            p.write_text("\n".join(lines), encoding="utf-8")
            sessions, causal_events, _stats, _errors = jp.parse_all(
                projects_dir=Path(d), since_days=30
            )
        self.assertIsInstance(causal_events, list)
        self.assertGreater(len(causal_events), 0)
        self.assertIsInstance(causal_events[0], jp.CausalEvent)


if __name__ == "__main__":
    unittest.main()
