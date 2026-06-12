# test_tool_output_bloat.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import CausalEvent  # noqa: E402


def _ev(session_id, content_size, event_type="tool_result", tool_name="Bash"):
    return CausalEvent(
        tool_use_id="tid",
        session_id=session_id,
        event_type=event_type,
        tool_name=tool_name,
        content_size=content_size,
    )


class TestToolOutputBloat(unittest.TestCase):

    def test_flags_when_avg_content_size_exceeds_threshold_and_enough_sessions(self):
        # 3 sessions, each with a single tool_result of 60_000 chars -> avg 60k > 50k
        events = [
            _ev("s1", 60_000),
            _ev("s2", 60_000),
            _ev("s3", 60_000),
        ]
        from detectors import tool_output_bloat
        leaks = tool_output_bloat.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "causal:tool_output_bloat")
        self.assertEqual(leaks[0].severity, "warning")
        self.assertEqual(leaks[0].basis, "causal")
        self.assertEqual(leaks[0].overlap_group, "tool_output")

    def test_no_flag_when_content_size_small(self):
        # 3 sessions, each with 1_000 chars -> avg 1k < 50k
        events = [
            _ev("s1", 1_000),
            _ev("s2", 1_000),
            _ev("s3", 1_000),
        ]
        from detectors import tool_output_bloat
        leaks = tool_output_bloat.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_no_flag_when_fewer_than_3_sessions(self):
        # 2 sessions with large content_size -> not enough sessions
        events = [
            _ev("s1", 100_000),
            _ev("s2", 100_000),
        ]
        from detectors import tool_output_bloat
        leaks = tool_output_bloat.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_no_flag_when_no_causal_events(self):
        from detectors import tool_output_bloat
        leaks = tool_output_bloat.detect([], [], None, None)
        self.assertEqual(leaks, [])

    def test_only_tool_result_events_counted(self):
        # Mix of event types — only tool_result should count
        events = [
            _ev("s1", 60_000, event_type="tool_result"),
            _ev("s2", 60_000, event_type="tool_result"),
            _ev("s3", 60_000, event_type="tool_result"),
            CausalEvent(tool_use_id="x", session_id="s4", event_type="other",
                        tool_name="Bash", content_size=999_999),
        ]
        from detectors import tool_output_bloat
        leaks = tool_output_bloat.detect([], events, None, None)
        # s4 has no tool_result events -> only 3 sessions qualify -> should flag
        self.assertEqual(len(leaks), 1)


if __name__ == "__main__":
    unittest.main()
