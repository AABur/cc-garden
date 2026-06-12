# test_repeated_reads.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import CausalEvent  # noqa: E402


def _read_ev(session_id, file_path, content_size, tool_name="Read"):
    return CausalEvent(
        tool_use_id="tid",
        session_id=session_id,
        event_type="tool_result",
        tool_name=tool_name,
        file_path=file_path,
        content_size=content_size,
    )


class TestRepeatedReads(unittest.TestCase):

    def test_flags_file_read_more_than_3_times_with_large_content(self):
        # Same file read 4 times in same session, each 3_000 chars -> total 12k >= 10k
        events = [_read_ev("s1", "/project/big_file.py", 3_000) for _ in range(4)]
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "causal:repeated_reads")
        self.assertEqual(leaks[0].severity, "suggestion")
        self.assertEqual(leaks[0].basis, "causal")
        self.assertIn("/project/big_file.py", leaks[0].evidence[0])
        self.assertIn("4", leaks[0].evidence[0])

    def test_no_flag_when_read_count_at_threshold(self):
        # Exactly 3 reads -> not OVER threshold (threshold is > 3)
        events = [_read_ev("s1", "/project/file.py", 5_000) for _ in range(3)]
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_no_flag_when_content_size_small(self):
        # File read 5 times but total content_size = 5 * 1_000 = 5_000 < 10_000
        events = [_read_ev("s1", "/project/tiny.py", 1_000) for _ in range(5)]
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_reads_in_different_sessions_not_combined(self):
        # Same file read 2 times each in 3 different sessions -> per-session count is 2 (not over threshold)
        events = (
            [_read_ev("s1", "/project/file.py", 5_000)] * 2 +
            [_read_ev("s2", "/project/file.py", 5_000)] * 2 +
            [_read_ev("s3", "/project/file.py", 5_000)] * 2
        )
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_edit_and_write_tools_also_counted(self):
        # 2 Read + 2 Edit in same session for same file = 4 total -> flag
        events = (
            [_read_ev("s1", "/project/file.py", 3_000, tool_name="Read")] * 2 +
            [_read_ev("s1", "/project/file.py", 3_000, tool_name="Edit")] * 2
        )
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)

    def test_no_flag_when_file_path_empty(self):
        # Events with empty file_path should be ignored
        events = [
            CausalEvent(
                tool_use_id="tid",
                session_id="s1",
                event_type="tool_result",
                tool_name="Read",
                file_path="",
                content_size=5_000,
            )
            for _ in range(5)
        ]
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
