#!/usr/bin/env python3
"""Self-contained tests for gather.py.

Runnable directly (pytest is NOT installed):

    python3 plugins/lucky-break/skills/lucky-break/scripts/test_gather.py

Functions are also named test_* so pytest could discover them. On success the
direct runner prints "ALL TESTS PASSED" and exits 0; on the first failing
assertion it prints the failure and exits 1.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Import the sibling gather.py by file path so the test works regardless of cwd.
_spec = importlib.util.spec_from_file_location("gather", SCRIPT_DIR / "gather.py")
assert _spec is not None and _spec.loader is not None
gather_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gather_mod)
gather = gather_mod.gather
gather_codex = gather_mod.gather_codex
gather_all = gather_mod.gather_all

# Fake secrets that MUST be scrubbed from the output.
SECRET_ANTHROPIC = "sk-ant-AAAAAAAAAAAAAAAAAAAA1234"
SECRET_AUTH_LINE = "Authorization: Bearer abc123"

# Literal working directory recorded inside Codex session_meta payloads.
CODEX_CWD = "/Users/test/Documents/demo"


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _build_root(tmp: Path) -> Path:
    """Create a temp Claude projects root with one project folder and several files."""
    root = tmp / "projects"
    proj = root / "-Users-test-Documents-demo"
    proj.mkdir(parents=True)

    # File 1: string-form user message, an assistant entry, a tool_result entry.
    _write_jsonl(
        proj / "session-a.jsonl",
        [
            {"type": "user", "message": {"content": "string form user message"}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "ASSISTANT_SHOULD_NOT_APPEAR"}
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "content": "TOOL_RESULT_SHOULD_NOT_APPEAR",
                        }
                    ]
                },
            },
        ],
    )

    # File 2: content[]-list user message, plus a user message with secrets.
    _write_jsonl(
        proj / "session-b.jsonl",
        [
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "text", "text": "list form user message"},
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": (
                        f"my key is {SECRET_ANTHROPIC}\n{SECRET_AUTH_LINE}"
                    )
                },
            },
            {"type": "system", "message": {"content": "SYSTEM_SHOULD_NOT_APPEAR"}},
        ],
    )

    # File 3: OLD mtime — must be excluded under days=7.
    old_proj = root / "-Users-test-Documents-old"
    old_proj.mkdir(parents=True)
    old_file = old_proj / "session-old.jsonl"
    _write_jsonl(
        old_file,
        [{"type": "user", "message": {"content": "OLD_PROJECT_SHOULD_BE_EXCLUDED"}}],
    )
    thirty_days_ago = time.time() - 30 * 86400
    os.utime(old_file, (thirty_days_ago, thirty_days_ago))

    return root


def _build_codex_root(tmp: Path) -> Path:
    """Create a temp Codex sessions root mirroring the real ~/.codex/sessions layout."""
    root = tmp / "sessions"
    day = root / "2026" / "06" / "06"
    day.mkdir(parents=True)

    # Interactive session: two genuine user_message events plus noise that must
    # be ignored (injected role=user context, assistant output).
    _write_jsonl(
        day / "rollout-2026-06-06T10-00-00-uuid1.jsonl",
        [
            {
                "type": "session_meta",
                "payload": {"cwd": CODEX_CWD, "thread_source": "interactive"},
            },
            {
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "codex prompt alpha"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "<environment_context> ENV_SHOULD_NOT_APPEAR </environment_context>",
                        }
                    ],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "CODEX_ASSISTANT_SHOULD_NOT_APPEAR"}
                    ],
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "user_message",
                    "message": f"codex secret {SECRET_ANTHROPIC}\n{SECRET_AUTH_LINE}",
                },
            },
        ],
    )

    # Second interactive session, SAME cwd -> must merge into one project entry.
    _write_jsonl(
        day / "rollout-2026-06-06T11-00-00-uuid2.jsonl",
        [
            {"type": "session_meta", "payload": {"cwd": CODEX_CWD}},
            {
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "codex prompt beta"},
            },
        ],
    )

    # Subagent session -> excluded entirely (synthetic, not user-initiated).
    _write_jsonl(
        day / "rollout-2026-06-06T12-00-00-uuid3.jsonl",
        [
            {
                "type": "session_meta",
                "payload": {"cwd": CODEX_CWD, "thread_source": "subagent"},
            },
            {
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "SUBAGENT_SHOULD_NOT_APPEAR"},
            },
        ],
    )

    # Old session -> excluded by mtime under days=7.
    old = day / "rollout-2026-06-06T09-00-00-uuidold.jsonl"
    _write_jsonl(
        old,
        [
            {"type": "session_meta", "payload": {"cwd": CODEX_CWD}},
            {
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "CODEX_OLD_SHOULD_BE_EXCLUDED"},
            },
        ],
    )
    thirty_days_ago = time.time() - 30 * 86400
    os.utime(old, (thirty_days_ago, thirty_days_ago))

    return root


def _all_samples(result: dict) -> list[str]:
    out: list[str] = []
    for proj in result["projects"]:
        out.extend(proj["samples"])
    return out


def _samples_from_entries(entries: list[dict]) -> list[str]:
    out: list[str] = []
    for proj in entries:
        out.extend(proj["samples"])
    return out


def test_contract_shape() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_root(Path(td))
        result = gather(root, days=7)

    assert set(result.keys()) == {"generated_at", "days", "projects"}, result.keys()
    assert isinstance(result["generated_at"], str)
    assert result["days"] == 7
    assert isinstance(result["projects"], list)
    for proj in result["projects"]:
        assert set(proj.keys()) == {
            "source",
            "path",
            "user_msg_count",
            "first_seen",
            "last_seen",
            "samples",
        }, proj.keys()
        assert proj["source"] in {"claude", "codex"}, proj["source"]
        assert isinstance(proj["path"], str)
        assert isinstance(proj["user_msg_count"], int)
        assert isinstance(proj["first_seen"], str)
        assert isinstance(proj["last_seen"], str)
        assert isinstance(proj["samples"], list)
        assert all(isinstance(s, str) for s in proj["samples"])


def test_only_user_text_captured() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_root(Path(td))
        result = gather(root, days=7)

    samples = _all_samples(result)
    blob = "\n".join(samples)
    assert "ASSISTANT_SHOULD_NOT_APPEAR" not in blob, "assistant text leaked"
    assert "TOOL_RESULT_SHOULD_NOT_APPEAR" not in blob, "tool_result text leaked"
    assert "SYSTEM_SHOULD_NOT_APPEAR" not in blob, "system text leaked"
    assert "string form user message" in blob, "string-form user message missing"
    assert "list form user message" in blob, "list-form user message missing"


def test_both_content_formats_parsed() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_root(Path(td))
        result = gather(root, days=7)

    samples = _all_samples(result)
    assert any("string form user message" == s for s in samples), "string form not parsed"
    assert any("list form user message" == s for s in samples), "list form not parsed"


def test_claude_source_tagged() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_root(Path(td))
        result = gather(root, days=7)

    assert result["projects"], "expected at least one claude project"
    assert all(p["source"] == "claude" for p in result["projects"]), (
        "claude entries must be tagged source=claude"
    )


def test_secrets_redacted() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_root(Path(td))
        result = gather(root, days=7)

    dumped = json.dumps(result, ensure_ascii=False)
    assert SECRET_ANTHROPIC not in dumped, "raw anthropic key leaked into output"
    assert "Bearer abc123" not in dumped, "raw Authorization bearer leaked into output"
    assert "[REDACTED:anthropic-key]" in dumped, "anthropic key not redacted"
    assert "[REDACTED]" in dumped, "Authorization header not redacted"


def test_old_project_excluded() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_root(Path(td))
        result = gather(root, days=7)

    paths = [p["path"] for p in result["projects"]]
    assert not any(p.endswith("-old") for p in paths), (
        f"old project should be excluded under days=7: {paths}"
    )
    samples = _all_samples(result)
    assert "OLD_PROJECT_SHOULD_BE_EXCLUDED" not in "\n".join(samples), (
        "old file content leaked"
    )


def test_sampling_cap_honored() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "projects"
        proj = root / "-Users-test-bulk"
        proj.mkdir(parents=True)
        records = [
            {"type": "user", "message": {"content": f"msg-{i}"}} for i in range(100)
        ]
        _write_jsonl(proj / "bulk.jsonl", records)

        result = gather(root, days=7, max_per_file=10)

    proj_entry = result["projects"][0]
    # max_per_file=10 -> first 5 + last 5 = 10 samples kept.
    assert len(proj_entry["samples"]) == 10, (
        f"expected 10 sampled messages, got {len(proj_entry['samples'])}"
    )
    # Full count is still reported, even though samples are capped.
    assert proj_entry["user_msg_count"] == 100, proj_entry["user_msg_count"]
    # First-half + last-half composition.
    assert proj_entry["samples"][0] == "msg-0", proj_entry["samples"][0]
    assert proj_entry["samples"][-1] == "msg-99", proj_entry["samples"][-1]


# --- Codex source tests -------------------------------------------------------


def test_codex_user_messages_captured() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_codex_root(Path(td))
        entries = gather_codex(root, days=7)

    assert len(entries) == 1, f"expected one merged codex project, got {len(entries)}"
    entry = entries[0]
    assert entry["source"] == "codex", entry["source"]
    assert entry["path"] == CODEX_CWD, entry["path"]

    samples = entry["samples"]
    blob = "\n".join(samples)
    assert "codex prompt alpha" in blob, "user_message alpha missing"
    assert "codex prompt beta" in blob, "user_message beta missing"
    # Noise that must NOT leak through:
    assert "ENV_SHOULD_NOT_APPEAR" not in blob, "injected environment_context leaked"
    assert "CODEX_ASSISTANT_SHOULD_NOT_APPEAR" not in blob, "assistant output leaked"
    # alpha + secret (file 1) + beta (file 2) = 3 user messages.
    assert entry["user_msg_count"] == 3, entry["user_msg_count"]


def test_codex_subagent_excluded() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_codex_root(Path(td))
        entries = gather_codex(root, days=7)

    blob = "\n".join(_samples_from_entries(entries))
    assert "SUBAGENT_SHOULD_NOT_APPEAR" not in blob, "subagent session leaked"


def test_codex_secrets_redacted() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_codex_root(Path(td))
        entries = gather_codex(root, days=7)

    dumped = json.dumps(entries, ensure_ascii=False)
    assert SECRET_ANTHROPIC not in dumped, "raw anthropic key leaked into codex output"
    assert "Bearer abc123" not in dumped, "raw Authorization bearer leaked into codex output"
    assert "[REDACTED:anthropic-key]" in dumped, "anthropic key not redacted in codex output"
    assert "[REDACTED]" in dumped, "Authorization header not redacted in codex output"


def test_codex_old_session_excluded() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = _build_codex_root(Path(td))
        entries = gather_codex(root, days=7)

    blob = "\n".join(_samples_from_entries(entries))
    assert "CODEX_OLD_SHOULD_BE_EXCLUDED" not in blob, "old codex session leaked"


def test_codex_sampling_cap_honored() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "sessions" / "2026" / "06" / "06"
        root.mkdir(parents=True)
        records: list[dict] = [{"type": "session_meta", "payload": {"cwd": CODEX_CWD}}]
        records += [
            {"type": "event_msg", "payload": {"type": "user_message", "message": f"cx-{i}"}}
            for i in range(100)
        ]
        _write_jsonl(root / "rollout-2026-06-06T10-00-00-bulk.jsonl", records)

        entries = gather_codex(Path(td) / "sessions", days=7, max_per_file=10)

    entry = entries[0]
    assert len(entry["samples"]) == 10, f"expected 10 samples, got {len(entry['samples'])}"
    assert entry["user_msg_count"] == 100, entry["user_msg_count"]
    assert entry["samples"][0] == "cx-0", entry["samples"][0]
    assert entry["samples"][-1] == "cx-99", entry["samples"][-1]


def test_codex_missing_root_is_empty() -> None:
    with tempfile.TemporaryDirectory() as td:
        entries = gather_codex(Path(td) / "does-not-exist", days=7)
    assert entries == [], entries


def test_gather_all_tags_both_sources() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        claude_root = _build_root(tmp / "claude")
        codex_root = _build_codex_root(tmp / "codex")
        result = gather_all(claude_root, codex_root, days=7)

    assert set(result.keys()) == {"generated_at", "days", "projects"}, result.keys()
    sources = {p["source"] for p in result["projects"]}
    assert sources == {"claude", "codex"}, sources
    # Both worlds present in the merged sample blob.
    blob = "\n".join(_all_samples(result))
    assert "string form user message" in blob, "claude samples missing from gather_all"
    assert "codex prompt alpha" in blob, "codex samples missing from gather_all"


def _run_all() -> int:
    tests = [
        test_contract_shape,
        test_only_user_text_captured,
        test_both_content_formats_parsed,
        test_claude_source_tagged,
        test_secrets_redacted,
        test_old_project_excluded,
        test_sampling_cap_honored,
        test_codex_user_messages_captured,
        test_codex_subagent_excluded,
        test_codex_secrets_redacted,
        test_codex_old_session_excluded,
        test_codex_sampling_cap_honored,
        test_codex_missing_root_is_empty,
        test_gather_all_tags_both_sources,
    ]
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"FAILED: {test.__name__}: {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors clearly
            print(f"ERROR: {test.__name__}: {exc!r}")
            return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(_run_all())
