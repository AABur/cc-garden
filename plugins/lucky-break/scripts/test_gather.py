#!/usr/bin/env python3
"""Self-contained tests for gather.py.

Runnable directly (pytest is NOT installed):

    python3 plugins/lucky-break/scripts/test_gather.py

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

# Fake secrets that MUST be scrubbed from the output.
SECRET_ANTHROPIC = "sk-ant-AAAAAAAAAAAAAAAAAAAA1234"
SECRET_AUTH_LINE = "Authorization: Bearer abc123"


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _build_root(tmp: Path) -> Path:
    """Create a temp projects root with one project folder and several files."""
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


def _all_samples(result: dict) -> list[str]:
    out: list[str] = []
    for proj in result["projects"]:
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
            "path",
            "user_msg_count",
            "first_seen",
            "last_seen",
            "samples",
        }, proj.keys()
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


def _run_all() -> int:
    tests = [
        test_contract_shape,
        test_only_user_text_captured,
        test_both_content_formats_parsed,
        test_secrets_redacted,
        test_old_project_excluded,
        test_sampling_cap_honored,
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
