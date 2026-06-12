# test_hook_injection_bloat.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import CausalEvent  # noqa: E402


def _hook(hook_name, hook_event, content_size, session_id="s1"):
    return CausalEvent(
        tool_use_id="tid",
        session_id=session_id,
        event_type="hook",
        hook_name=hook_name,
        hook_event=hook_event,
        content_size=content_size,
    )


def _tool_result(content_size, session_id="s1"):
    return CausalEvent(
        tool_use_id="tid",
        session_id=session_id,
        event_type="tool_result",
        tool_name="Bash",
        content_size=content_size,
    )


class TestHookInjectionBloat(unittest.TestCase):

    def test_flags_large_sessionstart_hook_above_threshold(self):
        # 20 fires of 12_000 chars each -> 240_000 chars -> 60_000 tokens >> 2_000 floor
        events = [_hook("SessionStart:clear", "SessionStart", 12_000) for _ in range(20)]
        from detectors import hook_injection_bloat
        leaks = hook_injection_bloat.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        leak = leaks[0]
        self.assertEqual(leak.id, "causal:hook_injection_bloat")
        self.assertEqual(leak.overlap_group, "hook_tax")
        self.assertEqual(leak.basis, "causal")
        self.assertIn("SessionStart:clear", leak.title)

    def test_no_flag_below_threshold(self):
        # Tiny injection: 5 fires of 100 chars -> 500 chars -> 125 tokens < 2_000
        events = [_hook("SessionStart:clear", "SessionStart", 100) for _ in range(5)]
        from detectors import hook_injection_bloat
        leaks = hook_injection_bloat.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_only_hook_events_count(self):
        # A pile of huge tool_result events must NOT trigger this detector.
        events = [_tool_result(999_999, session_id=f"s{i}") for i in range(10)]
        from detectors import hook_injection_bloat
        leaks = hook_injection_bloat.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_grouping_worst_hook_is_headline(self):
        # Two distinct hooks; the second has higher total_chars -> it is the headline.
        events = (
            [_hook("SessionStart:clear", "SessionStart", 5_000) for _ in range(5)]  # 25_000
            + [_hook("UserPromptSubmit:inject", "UserPromptSubmit", 10_000) for _ in range(10)]  # 100_000
        )
        from detectors import hook_injection_bloat
        leaks = hook_injection_bloat.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        leak = leaks[0]
        self.assertIn("UserPromptSubmit:inject", leak.title)
        evidence_text = "\n".join(leak.evidence)
        self.assertIn("UserPromptSubmit:inject", evidence_text)
        self.assertIn("SessionStart:clear", evidence_text)
        # est_weekly_tokens reports only the worst hook's cost (100_000 // 4 = 25_000),
        # not the aggregate of both hooks (125_000 // 4 = 31_250).
        worst_hook_tokens = 100_000 // 4  # UserPromptSubmit: 10 fires x 10_000 chars
        self.assertEqual(leak.est_weekly_tokens, worst_hook_tokens)

    def test_per_turn_note_present_for_sessionstart(self):
        events = [_hook("SessionStart:clear", "SessionStart", 12_000) for _ in range(20)]
        from detectors import hook_injection_bloat
        leaks = hook_injection_bloat.detect([], events, None, None)
        evidence_text = "\n".join(leaks[0].evidence)
        self.assertIn("every", evidence_text.lower())

    def test_per_turn_note_absent_for_stop_hook(self):
        # Stop hook is not per-turn; the note should be absent.
        events = [_hook("Stop:notify", "Stop", 12_000) for _ in range(20)]
        from detectors import hook_injection_bloat
        leaks = hook_injection_bloat.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        evidence_text = "\n".join(leaks[0].evidence).lower()
        self.assertNotIn("inject on every", evidence_text)
        self.assertNotIn("every qualifying turn", evidence_text)

    def test_est_weekly_tokens_is_observed_not_inflated(self):
        # 20 * 12_000 = 240_000 chars -> 240_000 // 4 = 60_000 tokens, no inflation.
        events = [_hook("SessionStart:clear", "SessionStart", 12_000) for _ in range(20)]
        from detectors import hook_injection_bloat
        leaks = hook_injection_bloat.detect([], events, None, None)
        self.assertEqual(leaks[0].est_weekly_tokens, 240_000 // 4)


if __name__ == "__main__":
    unittest.main()
