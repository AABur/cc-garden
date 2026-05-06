"""Unit tests for extract_sessions.py — stdlib unittest, no third-party deps."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import extract_sessions as ex  # noqa: E402


def make_event(line_no: int, **fields) -> str:
    base = {"timestamp": "2026-04-06T20:38:57.000Z", "uuid": f"u-{line_no}"}
    base.update(fields)
    return json.dumps(base)


class ParserTests(unittest.TestCase):
    def _emit(self, lines: list[str], source_kind: str = "main"):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "session.jsonl"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            sf = ex.SessionFile(
                path=path,
                session_id="11111111-aaaa-bbbb-cccc-222222222222",
                source_kind=source_kind,
            )
            stats = ex.Stats()
            events = list(ex.parse_session(sf, stats))
            return events, stats

    def test_user_string_content_emits_user_text(self):
        ev = make_event(
            1,
            type="user",
            message={"role": "user", "content": "build a thing"},
            cwd="/x",
            sessionId="s",
        )
        events, _ = self._emit([ev])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "user_text")
        self.assertEqual(events[0].text, "build a thing")

    def test_user_list_content_with_tool_result(self):
        body = "ok"
        ev = make_event(
            1,
            type="user",
            message={
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": body}]}
                ],
            },
        )
        events, _ = self._emit([ev])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "tool_result_short")
        self.assertEqual(events[0].text, body)

    def test_assistant_text_and_thinking_skip(self):
        ev = make_event(
            1,
            type="assistant",
            message={
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "secret-reasoning", "signature": "DO-NOT-LEAK"},
                    {"type": "text", "text": "I'll do that"},
                    {"type": "tool_use", "name": "Bash", "input": {"command": "ls -la"}},
                ],
            },
        )
        events, stats = self._emit([ev])
        kinds = [e.kind for e in events]
        self.assertIn("assistant_text", kinds)
        self.assertIn("tool_use", kinds)
        self.assertNotIn("thinking", kinds)
        for e in events:
            self.assertNotIn("DO-NOT-LEAK", e.text)
            self.assertNotIn("secret-reasoning", e.text)
        self.assertEqual(stats.thinking_blocks_seen, 1)
        self.assertEqual(stats.thinking_blocks_omitted, 1)

    def test_skip_event_types_dropped(self):
        lines = [
            json.dumps({"type": "permission-mode", "permissionMode": "plan"}),
            json.dumps({"type": "file-history-snapshot"}),
            json.dumps({"type": "system", "subtype": "turn_duration"}),
            json.dumps({"type": "attachment", "data": "..."}),
            make_event(5, type="user", message={"role": "user", "content": "hello"}),
        ]
        events, _ = self._emit(lines)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "user_text")

    def test_malformed_line_counted_not_raised(self):
        lines = [
            "{not-json",
            make_event(2, type="user", message={"role": "user", "content": "ok"}),
        ]
        events, stats = self._emit(lines)
        self.assertEqual(len(events), 1)
        self.assertEqual(stats.malformed_lines, 1)

    def test_summary_event_kept_lower_confidence(self):
        ev = json.dumps({"type": "summary", "summary": "the gist"})
        events, _ = self._emit([ev])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "summary")
        self.assertEqual(events[0].confidence, "summary-derived")


class RedactionTests(unittest.TestCase):
    def _redact(self, text: str) -> tuple[str, ex.Stats]:
        s = ex.Stats()
        return ex.redact(text, s), s

    def test_redacts_anthropic_key(self):
        text = "key sk-ant-abcDEF1234567890abcdef please"
        out, stats = self._redact(text)
        self.assertNotIn("sk-ant-abcDEF1234567890abcdef", out)
        self.assertIn("[REDACTED:anthropic-key]", out)
        self.assertEqual(stats.redactions["[REDACTED:anthropic-key]"], 1)

    def test_redacts_github_pat(self):
        text = "token ghp_abcdefghijklmnopqrst1234"
        out, _ = self._redact(text)
        self.assertIn("[REDACTED:github-pat]", out)

    def test_redacts_aws_and_jwt_and_auth_header(self):
        text = (
            "AKIAABCDEFGHIJKLMNOP\n"
            "eyJhbcdefGHI.eyJpYXQbmFtZQOiJqb2hubnk.dBjftJeZ4CVPmB92Tz9q\n"
            "Authorization: Bearer abcdef\n"
        )
        out, stats = self._redact(text)
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", out)
        self.assertIn("[REDACTED:aws-key]", out)
        self.assertIn("[REDACTED:jwt]", out)
        self.assertIn("[REDACTED]", out)
        self.assertNotIn("Bearer abcdef", out)
        self.assertGreaterEqual(sum(stats.redactions.values()), 3)


class ClassifierTests(unittest.TestCase):
    def test_short_tool_result(self):
        kind, body = ex._classify_tool_result("ok")
        self.assertEqual(kind, "tool_result_short")
        self.assertEqual(body, "ok")

    def test_metadata_for_huge_result(self):
        body = "X" * (ex.LARGE_TOOL_RESULT_CHARS + 10)
        kind, out = ex._classify_tool_result(body)
        self.assertEqual(kind, "tool_result_metadata")
        self.assertIn("omitted", out)

    def test_summary_for_signal_pattern(self):
        body = "Traceback (most recent call last):\n" + ("more " * 200)
        kind, out = ex._classify_tool_result(body)
        self.assertEqual(kind, "tool_result_summary")


class BudgetTests(unittest.TestCase):
    def _make_event(self, kind: str, text: str, sidechain: bool = False, ts: str = "2026-04-01T00:00:00Z") -> ex.Event:
        return ex.Event(
            kind=kind,
            text=text,
            timestamp=ts,
            session_id="s",
            session_short="s0",
            uuid="u",
            parent_uuid=None,
            git_branch="main",
            cwd="/x",
            line=1,
            is_sidechain=sidechain,
            source_kind="sidechain" if sidechain else "main",
        )

    def test_budget_caps_total_chars(self):
        events = [self._make_event("user_text", "U" * 200) for _ in range(20)]
        stats = ex.Stats()
        kept = ex.apply_budget(events, budget=1000, stats=stats)
        self.assertLess(stats.chars_included, 1100)
        self.assertLess(len(kept), len(events))

    def test_subagent_separate_25pct_cap(self):
        main = [self._make_event("user_text", "M" * 100, sidechain=False, ts=f"2026-04-01T00:0{i:01d}:00Z") for i in range(10)]
        side = [self._make_event("user_text", "S" * 100, sidechain=True, ts=f"2026-04-02T00:0{i:01d}:00Z") for i in range(20)]
        stats = ex.Stats()
        kept = ex.apply_budget(main + side, budget=1000, stats=stats)
        # Sidechain pool capped at ~250 chars; with overhead per-event ~80, accept at most ~3 events
        kept_side = [e for e in kept if e.is_sidechain]
        self.assertLessEqual(stats.sidechain_chars_included, 1000 * ex.SUBAGENT_BUDGET_FRACTION + 100 + 80)
        self.assertGreater(len(kept_side), 0)

    def test_user_text_prioritised_over_tool_use(self):
        budget = 500
        # Older user_text + newer tool_use; with budget all user_text fits but tool_use may not
        events = []
        for i in range(3):
            events.append(self._make_event("user_text", "U" * 100, ts=f"2026-04-01T00:0{i}:00Z"))
        for i in range(20):
            events.append(self._make_event("tool_use", "[tool_use Bash]", ts=f"2026-04-02T00:0{i:02d}:00Z"))
        stats = ex.Stats()
        kept = ex.apply_budget(events, budget=budget, stats=stats)
        kinds = {e.kind for e in kept}
        self.assertIn("user_text", kinds)


class FlatEncodeTests(unittest.TestCase):
    def test_underscore_becomes_dash(self):
        # Bug found in tgfolder_analyzer: Claude Code replaces _ with -
        result = ex.flat_encode(Path("/Users/aabur/Documents/GitHub/AABur/tgfolder_analyzer"))
        self.assertEqual(result, "-Users-aabur-Documents-GitHub-AABur-tgfolder-analyzer")

    def test_dot_becomes_dash(self):
        # /.paperclip/ becomes --paperclip- (slash + dot both become dash)
        result = ex.flat_encode(Path("/Users/aabur/.paperclip/instances"))
        self.assertEqual(result, "-Users-aabur--paperclip-instances")

    def test_existing_dashes_preserved(self):
        result = ex.flat_encode(Path("/Users/aabur/Documents/GitHub/AABur/Kards-claude"))
        self.assertEqual(result, "-Users-aabur-Documents-GitHub-AABur-Kards-claude")

    def test_alphanumeric_uppercase_preserved(self):
        result = ex.flat_encode(Path("/Users/aabur/Documents/GitHub/AABur/Convert2MD-Bot"))
        self.assertEqual(result, "-Users-aabur-Documents-GitHub-AABur-Convert2MD-Bot")


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "myrepo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.repo, check=True)
        self.projects = self.tmp / "projects"
        self.projects.mkdir()
        self._orig_projects = ex.PROJECTS_DIR
        ex.PROJECTS_DIR = self.projects

    def tearDown(self):
        ex.PROJECTS_DIR = self._orig_projects
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _flat(self, p: Path) -> str:
        return ex.flat_encode(p)

    def _write_jsonl(self, dir_: Path, name: str, events: list[dict]) -> Path:
        dir_.mkdir(parents=True, exist_ok=True)
        path = dir_ / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for ev in events:
                fh.write(json.dumps(ev) + "\n")
        return path

    def test_first_non_null_cwd_skips_permission_mode_opener(self):
        flat = self._flat(self.repo)
        d = self.projects / flat
        self._write_jsonl(
            d,
            "abc",
            [
                {"type": "permission-mode", "permissionMode": "plan"},
                {"type": "file-history-snapshot"},
                {
                    "type": "user",
                    "message": {"role": "user", "content": "hi"},
                    "cwd": str(self.repo),
                    "uuid": "u1",
                    "timestamp": "2026-04-01T00:00:00Z",
                },
            ],
        )
        stats = ex.Stats()
        sessions = ex.discover_sessions(self.repo, stats)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].cwd_first, str(self.repo))
        self.assertEqual(sessions[0].source_kind, "main")

    def test_precise_glob_rejects_sibling_with_shared_prefix(self):
        flat = self._flat(self.repo)
        good = self.projects / flat
        sibling = self.projects / f"{flat}-pytest-guide"
        self._write_jsonl(good, "g", [{"type": "user", "message": {"role": "user", "content": "x"}, "cwd": str(self.repo)}])
        self._write_jsonl(
            sibling,
            "s",
            [{"type": "user", "message": {"role": "user", "content": "x"}, "cwd": str(self.repo) + "-pytest-guide"}],
        )
        stats = ex.Stats()
        sessions = ex.discover_sessions(self.repo, stats)
        accepted_paths = [s.path for s in sessions]
        self.assertTrue(any("/g.jsonl" in str(p) for p in accepted_paths))
        self.assertFalse(any("/s.jsonl" in str(p) for p in accepted_paths))

    def test_worktree_dir_pattern_accepted(self):
        flat = self._flat(self.repo)
        worktree_name = f"{flat}--claude-worktrees-feature-abc"
        d = self.projects / worktree_name
        wt_path = self.tmp / "myrepo--claude-worktrees-feature-abc"
        self._write_jsonl(
            d,
            "w",
            [
                {
                    "type": "user",
                    "message": {"role": "user", "content": "x"},
                    "cwd": str(wt_path),
                    "timestamp": "2026-04-02T00:00:00Z",
                }
            ],
        )
        stats = ex.Stats()
        sessions = ex.discover_sessions(self.repo, stats)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].source_kind, "worktree")

    def test_subagent_jsonl_collected_and_tagged(self):
        flat = self._flat(self.repo)
        d = self.projects / flat
        self._write_jsonl(d, "main", [{"type": "user", "message": {"role": "user", "content": "x"}, "cwd": str(self.repo)}])
        sub_dir = d / "main" / "subagents"
        self._write_jsonl(
            sub_dir,
            "agent-xyz",
            [
                {
                    "type": "user",
                    "message": {"role": "user", "content": "explore"},
                    "isSidechain": True,
                    "cwd": str(self.repo),
                }
            ],
        )
        stats = ex.Stats()
        sessions = ex.discover_sessions(self.repo, stats)
        kinds = {s.source_kind for s in sessions}
        self.assertIn("main", kinds)
        self.assertIn("sidechain", kinds)


class FullPipelineSmokeTest(unittest.TestCase):
    def test_run_no_sessions_returns_clean_status(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            with tempfile.TemporaryDirectory() as projects:
                orig = ex.PROJECTS_DIR
                ex.PROJECTS_DIR = Path(projects)
                try:
                    out = ex.run(repo.resolve(), ex.DEFAULT_BUDGET_CHARS)
                    self.assertEqual(out["status"], "no_sessions")
                finally:
                    ex.PROJECTS_DIR = orig


if __name__ == "__main__":
    unittest.main()
