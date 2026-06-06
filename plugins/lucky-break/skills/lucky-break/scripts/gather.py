#!/usr/bin/env python3
"""Gather last-N-days user messages from Claude Code and Codex CLI transcripts.

READ-ONLY: this script only reads session log files under the Claude Code
projects directory (``~/.claude/projects``) and the Codex CLI sessions directory
(``~/.codex/sessions``). It never writes any file, makes no network calls, and
runs no git commands. It streams each transcript line-by-line, extracts the
user's own messages, redacts secrets, samples them, groups them by project, and
prints a single compact JSON object to stdout.

Each project entry is tagged with ``source`` (``"claude"`` or ``"codex"``) so the
same repository worked on through both CLIs appears as two entries that the
caller treats together.

Stdlib-only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ported verbatim from plugins/retro/scripts/extract_sessions.py — the proven,
# stdlib-only redaction list by the same author. Applied to every sample.
SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{16,}"), "[REDACTED:anthropic-key]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "[REDACTED:openai-key]"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "[REDACTED:github-pat]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "[REDACTED:github-pat]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "[REDACTED:slack-token]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED:aws-key]"),
    (
        re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),
        "[REDACTED:jwt]",
    ),
    (re.compile(r"(?im)^(\s*Authorization:\s*)\S+"), r"\1[REDACTED]"),
]


def redact(text: str) -> str:
    """Apply every secret pattern to a single sample, returning the redacted text."""
    out = text
    for pat, repl in SECRET_PATTERNS:
        out = pat.sub(repl, out)
    return out


def extract_text(msg: Any) -> str:
    """Unpack message content: string form OR content[] list of {type:text} items."""
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                t = item.get("text")
                if isinstance(t, str):
                    parts.append(t)
        return " ".join(parts)
    return ""


def _iso(ts: float) -> str:
    """Convert a POSIX timestamp into a local-time ISO 8601 string."""
    return datetime.fromtimestamp(ts).isoformat()


def _sample(samples: list[str], max_per_file: int) -> list[str]:
    """Keep the first half plus the last half to capture early and late activity."""
    half = max(max_per_file // 2, 0)
    if half == 0:
        return samples[:max_per_file] if max_per_file > 0 else []
    if len(samples) <= 2 * half:
        return list(samples)
    return samples[:half] + samples[-half:]


def _merge_entry(
    projects: dict[str, dict],
    key: str,
    *,
    source: str,
    path: str,
    full_count: int,
    sampled: list[str],
    seen: str,
) -> None:
    """Accumulate one file's contribution into the grouped project map in place."""
    entry = projects.get(key)
    if entry is None:
        projects[key] = {
            "source": source,
            "path": path,
            "user_msg_count": full_count,
            "first_seen": seen,
            "last_seen": seen,
            "samples": list(sampled),
        }
        return
    entry["user_msg_count"] += full_count
    if seen < entry["first_seen"]:
        entry["first_seen"] = seen
    if seen > entry["last_seen"]:
        entry["last_seen"] = seen
    entry["samples"].extend(sampled)


def gather_claude(root: Path, days: int = 7, max_per_file: int = 200) -> list[dict]:
    """Collect recent user messages from Claude Code transcripts under `root`.

    Streams every *.jsonl file modified within the last `days` days, keeps only
    user-authored text messages (skipping assistant/system/tool_result entries),
    redacts secrets, samples up to `max_per_file` messages per file (first half
    plus last half), and groups results by project folder name.

    Args:
        root: The Claude Code projects directory to walk (passed explicitly so
            tests can supply a temporary directory).
        days: Look back this many days based on each file's mtime.
        max_per_file: Maximum number of sampled messages kept per file.

    Returns:
        A list of project entries, each tagged ``source: "claude"``.
    """
    cutoff = time.time() - days * 86400
    projects: dict[str, dict] = {}

    if not root.exists():
        return []

    for f in sorted(root.rglob("*.jsonl")):
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue

        samples: list[str] = []
        try:
            fh = f.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except (ValueError, json.JSONDecodeError):
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get("type") != "user":
                    continue
                if "message" not in rec:
                    continue
                text = extract_text(rec.get("message")).strip()
                if not text:
                    continue
                samples.append(redact(text))

        if not samples:
            continue

        seen = _iso(mtime)
        _merge_entry(
            projects,
            f.parent.name,
            source="claude",
            path=str(f.parent),
            full_count=len(samples),
            sampled=_sample(samples, max_per_file),
            seen=seen,
        )

    return list(projects.values())


def gather_codex(root: Path, days: int = 7, max_per_file: int = 200) -> list[dict]:
    """Collect recent user messages from Codex CLI sessions under `root`.

    Codex stores one session per ``rollout-*.jsonl`` file under
    ``sessions/YYYY/MM/DD/``. Each line is an envelope ``{timestamp, type,
    payload}``. The cleanest signal for what the human actually typed is the
    ``event_msg`` record whose ``payload.type == "user_message"`` (its
    ``payload.message`` carries the raw prompt without the injected AGENTS.md /
    environment_context blocks that ride along on ``role: "user"`` items).

    Sessions spawned for sub-agents (``session_meta.payload.thread_source ==
    "subagent"``) carry synthetic prompts, not user reflection, and are skipped
    entirely. Results are grouped by the session's working directory
    (``session_meta.payload.cwd``).

    Args:
        root: The Codex sessions directory to walk (``~/.codex/sessions``).
        days: Look back this many days based on each file's mtime.
        max_per_file: Maximum number of sampled messages kept per file.

    Returns:
        A list of project entries, each tagged ``source: "codex"``.
    """
    cutoff = time.time() - days * 86400
    projects: dict[str, dict] = {}

    if not root.exists():
        return []

    for f in sorted(root.rglob("rollout-*.jsonl")):
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue

        cwd: str | None = None
        is_subagent = False
        samples: list[str] = []
        try:
            fh = f.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except (ValueError, json.JSONDecodeError):
                    continue
                if not isinstance(rec, dict):
                    continue
                payload = rec.get("payload")
                if not isinstance(payload, dict):
                    continue
                rec_type = rec.get("type")
                if rec_type == "session_meta":
                    c = payload.get("cwd")
                    if isinstance(c, str) and c:
                        cwd = c
                    if payload.get("thread_source") == "subagent":
                        is_subagent = True
                elif rec_type == "event_msg" and payload.get("type") == "user_message":
                    msg = payload.get("message")
                    if isinstance(msg, str):
                        text = msg.strip()
                        if text:
                            samples.append(redact(text))

        if is_subagent or not samples:
            continue

        key = cwd if cwd else str(f.parent)
        seen = _iso(mtime)
        _merge_entry(
            projects,
            key,
            source="codex",
            path=key,
            full_count=len(samples),
            sampled=_sample(samples, max_per_file),
            seen=seen,
        )

    return list(projects.values())


def gather_all(
    claude_root: Path,
    codex_root: Path,
    days: int = 7,
    max_per_file: int = 200,
    sources: tuple[str, ...] = ("claude", "codex"),
) -> dict:
    """Combine Claude and Codex project entries into the single output contract."""
    projects: list[dict] = []
    if "claude" in sources:
        projects.extend(gather_claude(claude_root, days=days, max_per_file=max_per_file))
    if "codex" in sources:
        projects.extend(gather_codex(codex_root, days=days, max_per_file=max_per_file))
    return {
        "generated_at": datetime.now().isoformat(),
        "days": days,
        "projects": projects,
    }


def gather(root: Path, days: int = 7, max_per_file: int = 200) -> dict:
    """Claude-only convenience wrapper returning the full output contract.

    Retained for backward compatibility; new callers should prefer
    :func:`gather_all`.
    """
    return {
        "generated_at": datetime.now().isoformat(),
        "days": days,
        "projects": gather_claude(root, days=days, max_per_file=max_per_file),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gather recent user messages from Claude Code and Codex CLI "
            "transcripts (read-only)."
        ),
    )
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default 7).")
    parser.add_argument(
        "--max-per-file",
        type=int,
        default=200,
        help="Maximum sampled messages per file (default 200).",
    )
    parser.add_argument(
        "--source",
        choices=["claude", "codex", "both"],
        default="both",
        help="Which CLI logs to read (default both).",
    )
    args = parser.parse_args(argv)

    sources: tuple[str, ...]
    if args.source == "both":
        sources = ("claude", "codex")
    else:
        sources = (args.source,)

    claude_root = Path.home() / ".claude" / "projects"
    codex_root = Path.home() / ".codex" / "sessions"
    result = gather_all(
        claude_root,
        codex_root,
        days=args.days,
        max_per_file=args.max_per_file,
        sources=sources,
    )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
