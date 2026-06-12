# test_bash_antipatterns.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import CausalEvent  # noqa: E402


def _bash_ev(session_id, command_head):
    return CausalEvent(
        tool_use_id="tid",
        session_id=session_id,
        event_type="tool_result",
        tool_name="Bash",
        command_head=command_head,
        content_size=100,
    )


class TestBashAntipatterns(unittest.TestCase):

    def _make_events(self, cmd, count):
        return [_bash_ev(f"s{i}", cmd) for i in range(count)]

    def test_detects_cat_head_tail_commands(self):
        # 12 cat calls -> above MIN_COUNT=10
        events = self._make_events("cat /some/file.py", 12)
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "causal:bash_antipatterns")
        self.assertEqual(leaks[0].severity, "suggestion")
        self.assertEqual(leaks[0].basis, "causal")
        self.assertIn("12", leaks[0].evidence[0])

    def test_detects_mixed_shell_readers(self):
        # 4 cat + 4 grep + 4 head = 12 total
        events = (
            self._make_events("cat file.txt", 4) +
            self._make_events("grep pattern file.txt", 4) +
            self._make_events("head -n 20 file.txt", 4)
        )
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)

    def test_no_flag_when_below_min_count(self):
        # Only 5 cat calls -> below MIN_COUNT=10
        events = self._make_events("cat /some/file.py", 5)
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_non_bash_tools_not_counted(self):
        # 12 Read tool events -> tool_name is "Read", not "Bash"
        events = [
            CausalEvent(
                tool_use_id="tid",
                session_id=f"s{i}",
                event_type="tool_result",
                tool_name="Read",
                command_head="cat /file",   # command_head has cat but tool is Read
                content_size=100,
            )
            for i in range(12)
        ]
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_non_shell_bash_commands_not_counted(self):
        # 12 Bash calls with non-shell-reader command
        events = self._make_events("git status", 12)
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_empty_command_head_skipped(self):
        events = [
            CausalEvent(
                tool_use_id="tid",
                session_id=f"s{i}",
                event_type="tool_result",
                tool_name="Bash",
                command_head="",
                content_size=100,
            )
            for i in range(20)
        ]
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
