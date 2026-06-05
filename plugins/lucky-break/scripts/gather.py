#!/usr/bin/env python3
"""Gather last-N-days user messages from Claude Code transcripts.

READ-ONLY: this script only reads JSONL session files under the Claude Code
projects directory. It never writes any file, makes no network calls, and
runs no git commands. It streams each transcript line-by-line, extracts the
user's own messages, redacts secrets, samples them, groups them by project
folder, and prints a single compact JSON object to stdout.

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


def gather(root: Path, days: int = 7, max_per_file: int = 200) -> dict:
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
        A dict matching the output contract documented in the module/README.
    """
    cutoff = time.time() - days * 86400
    half = max(max_per_file // 2, 0)

    projects: dict[str, dict] = {}

    if not root.exists():
        return {
            "generated_at": datetime.now().isoformat(),
            "days": days,
            "projects": [],
        }

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

        # Sample: first half + last half to capture both early and late activity.
        if half == 0:
            sampled = samples[: max_per_file] if max_per_file > 0 else []
        elif len(samples) <= 2 * half:
            sampled = samples
        else:
            sampled = samples[:half] + samples[-half:]

        proj_name = f.parent.name
        first_seen = _iso(mtime)
        last_seen = _iso(mtime)

        if proj_name not in projects:
            projects[proj_name] = {
                "path": str(f.parent),
                "user_msg_count": 0,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "samples": [],
            }
        entry = projects[proj_name]
        entry["user_msg_count"] += len(samples)
        if first_seen < entry["first_seen"]:
            entry["first_seen"] = first_seen
        if last_seen > entry["last_seen"]:
            entry["last_seen"] = last_seen
        entry["samples"].extend(sampled)

    return {
        "generated_at": datetime.now().isoformat(),
        "days": days,
        "projects": list(projects.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gather recent user messages from Claude Code transcripts (read-only).",
    )
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default 7).")
    parser.add_argument(
        "--max-per-file",
        type=int,
        default=200,
        help="Maximum sampled messages per file (default 200).",
    )
    args = parser.parse_args(argv)

    root = Path.home() / ".claude" / "projects"
    result = gather(root, days=args.days, max_per_file=args.max_per_file)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
