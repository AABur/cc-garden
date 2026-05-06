#!/usr/bin/env python3
"""Deterministic Claude Code JSONL parser for the /retro skill.

Discovers session JSONL files for a project, walks nested message.content[],
applies the evidence policy with secret redaction and a character budget,
and writes evidence.md, source-map.json, stats.json. A summary JSON object
is printed to stdout for the calling skill to consume.

Stdlib-only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

PROJECTS_DIR = Path.home() / ".claude" / "projects"

DEFAULT_BUDGET_CHARS = 320_000
SUBAGENT_BUDGET_FRACTION = 0.25
TOKEN_PER_CHAR = 0.25  # rough display-only estimate

SHORT_TOOL_RESULT_CHARS = 500
LARGE_TOOL_RESULT_CHARS = 50_000
TOOL_RESULT_SUMMARY_CHARS = 1_500
LONG_TEXT_TRUNCATE = 8_000
PASTED_BLOCK_THRESHOLD = 4_000

SKIP_EVENT_TYPES = {
    "permission-mode",
    "file-history-snapshot",
    "custom-title",
    "agent-name",
    "pr-link",
    "last-prompt",
    "queue-operation",
    "attachment",
    "system",
}

WORKTREE_PATTERN = re.compile(r"--claude-worktrees-")

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

TOOL_RESULT_SIGNAL_PATTERNS = [
    re.compile(r"\bTraceback\b"),
    re.compile(r"\bFAILED\b"),
    re.compile(r"\bError:\s"),
    re.compile(r"^\s*deleted file mode", re.MULTILINE),
    re.compile(r"^\s*new file mode", re.MULTILINE),
    re.compile(r"^On branch ", re.MULTILINE),
    re.compile(r"^nothing to commit", re.MULTILINE),
]


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass
class Stats:
    sessions_discovered: int = 0
    sessions_accepted: int = 0
    sessions_rejected: int = 0
    rejected_dirs: list[str] = field(default_factory=list)
    rejected_sessions: list[dict[str, str]] = field(default_factory=list)
    events_by_kind: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    thinking_blocks_seen: int = 0
    thinking_blocks_omitted: int = 0
    malformed_lines: int = 0
    redactions: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    truncations: int = 0
    pasted_blocks_omitted: int = 0
    omitted_by_category: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    omitted_events_by_kind: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    chars_included: int = 0
    chars_total_raw: int = 0
    estimated_tokens_included: int = 0
    sidechain_chars_included: int = 0
    sidechain_chars_omitted: int = 0
    main_chars_included: int = 0
    main_chars_omitted: int = 0
    date_min: str | None = None
    date_max: str | None = None
    budget_chars: int = DEFAULT_BUDGET_CHARS

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("events_by_kind", "redactions", "omitted_by_category", "omitted_events_by_kind"):
            d[k] = dict(d[k])
        return d


@dataclass
class SessionFile:
    path: Path
    session_id: str
    source_kind: str  # "main" | "worktree" | "sidechain"
    parent_session_id: str | None = None  # for sidechain
    cwd_first: str | None = None
    accepted: bool = True
    reject_reason: str | None = None


@dataclass
class Event:
    kind: str  # user_text | assistant_text | tool_result_short | tool_result_summary | tool_result_metadata | tool_use | summary
    text: str
    timestamp: str | None
    session_id: str
    session_short: str
    uuid: str | None
    parent_uuid: str | None
    git_branch: str | None
    cwd: str | None
    line: int
    is_sidechain: bool
    source_kind: str
    confidence: str = "direct"

    @property
    def char_len(self) -> int:
        return len(self.text)


# ---------------------------------------------------------------------------
# Project root resolution
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip()
    except FileNotFoundError:
        return 127, ""


def resolve_project_root(start: Path) -> tuple[Path | None, str | None]:
    """Return (root_path, error_message). Exactly one is None."""
    code, out = _git(["rev-parse", "--show-toplevel"], start)
    if code == 0 and out:
        return Path(out).resolve(), None
    git_children = [p for p in start.iterdir() if p.is_dir() and (p / ".git").exists()] if start.is_dir() else []
    if len(git_children) > 1:
        return None, (
            "Multiple git repositories detected in the current directory. "
            "/retro must be run from inside one specific repository, not a parent folder."
        )
    return None, (
        "/retro requires a git repository. Initialize one with `git init` "
        "or run /retro inside an existing repo."
    )


FLAT_ENCODE_RE = re.compile(r"[^A-Za-z0-9-]")


def flat_encode(path: Path) -> str:
    """Encode an absolute path the same way Claude Code does for ~/.claude/projects/.

    Replaces every character outside [A-Za-z0-9-] with `-`. This matches Claude
    Code's own encoding — observed empirically: `/`, `_`, `.` all become `-`.
    """
    s = str(path.resolve())
    return FLAT_ENCODE_RE.sub("-", s)


def _is_within(child: Path, parent: Path) -> bool:
    if child == parent:
        return True
    return parent in child.parents


def decode_flat(name: str) -> str:
    return name.replace("-", "/")


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------


def discover_sessions(root: Path, stats: Stats) -> list[SessionFile]:
    flat_root = flat_encode(root)
    flat_root_dir = PROJECTS_DIR / flat_root

    candidate_dirs: list[tuple[Path, str]] = []  # (dir, source_kind)
    if not PROJECTS_DIR.exists():
        return []

    if flat_root_dir.exists() and flat_root_dir.is_dir():
        candidate_dirs.append((flat_root_dir, "main"))

    parent_root = root.resolve()
    for entry in sorted(PROJECTS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name == flat_root:
            continue
        if not name.startswith(flat_root):
            continue
        suffix = name[len(flat_root):]
        if WORKTREE_PATTERN.match(suffix):
            candidate_dirs.append((entry, "worktree"))
            continue
        if not suffix.startswith("-"):
            stats.rejected_dirs.append(f"{name} (prefix-collision, not a subdir)")
            continue
        decoded = parent_root / decode_flat(suffix[1:])
        try:
            decoded_resolved = decoded.resolve(strict=False)
            if _is_within(decoded_resolved, parent_root):
                candidate_dirs.append((entry, "main"))
            else:
                stats.rejected_dirs.append(f"{name} (decoded path outside root)")
        except Exception:
            stats.rejected_dirs.append(f"{name} (decode failed)")

    sessions: list[SessionFile] = []
    for d, source_kind in candidate_dirs:
        for jsonl in sorted(d.glob("*.jsonl")):
            sf = _attribute_session(jsonl, root, source_kind, stats)
            if sf is not None:
                sessions.append(sf)
        for sub_jsonl in sorted(d.glob("*/subagents/*.jsonl")):
            parent_id = sub_jsonl.parent.parent.name
            sf = _attribute_session(sub_jsonl, root, "sidechain", stats, parent_id)
            if sf is not None:
                sessions.append(sf)
    return sessions


def _attribute_session(
    jsonl: Path,
    root: Path,
    source_kind: str,
    stats: Stats,
    parent_session_id: str | None = None,
) -> SessionFile | None:
    stats.sessions_discovered += 1
    session_id = jsonl.stem
    cwd = _first_non_null_cwd(jsonl)
    if source_kind == "worktree" or source_kind == "sidechain":
        stats.sessions_accepted += 1
        return SessionFile(
            path=jsonl,
            session_id=session_id,
            source_kind=source_kind,
            parent_session_id=parent_session_id,
            cwd_first=cwd,
            accepted=True,
        )
    if cwd is None:
        stats.sessions_accepted += 1
        return SessionFile(
            path=jsonl,
            session_id=session_id,
            source_kind=source_kind,
            cwd_first=None,
            accepted=True,
        )
    try:
        cwd_resolved = Path(cwd).resolve(strict=False)
    except Exception:
        cwd_resolved = Path(cwd)
    try:
        root_resolved = root.resolve(strict=False)
    except Exception:
        root_resolved = root
    if _is_within(cwd_resolved, root_resolved):
        stats.sessions_accepted += 1
        return SessionFile(
            path=jsonl,
            session_id=session_id,
            source_kind=source_kind,
            cwd_first=cwd,
            accepted=True,
        )
    stats.sessions_rejected += 1
    stats.rejected_sessions.append({"path": str(jsonl), "cwd": cwd, "reason": "cwd outside root"})
    return None


def _first_non_null_cwd(jsonl: Path, max_lines: int = 200) -> str | None:
    try:
        with jsonl.open("r", encoding="utf-8", errors="replace") as fh:
            for i, raw in enumerate(fh, 1):
                if i > max_lines:
                    break
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    ev = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                cwd = ev.get("cwd")
                if isinstance(cwd, str) and cwd:
                    return cwd
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------
# JSONL parsing
# ---------------------------------------------------------------------------


def parse_session(sf: SessionFile, stats: Stats) -> Iterator[Event]:
    try:
        fh = sf.path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for ln, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                stats.malformed_lines += 1
                continue
            etype = ev.get("type")
            if etype in SKIP_EVENT_TYPES:
                continue
            yield from _emit_events(ev, ln, sf, stats, etype)


def _emit_events(
    ev: dict[str, Any], ln: int, sf: SessionFile, stats: Stats, etype: str
) -> Iterator[Event]:
    base = {
        "timestamp": ev.get("timestamp"),
        "session_id": sf.session_id,
        "session_short": sf.session_id[:8],
        "uuid": ev.get("uuid"),
        "parent_uuid": ev.get("parentUuid"),
        "git_branch": ev.get("gitBranch"),
        "cwd": ev.get("cwd"),
        "line": ln,
        "is_sidechain": bool(ev.get("isSidechain", sf.source_kind == "sidechain")),
        "source_kind": sf.source_kind,
    }

    if etype == "summary":
        text = ev.get("summary") or ev.get("text") or ""
        if isinstance(text, str) and text.strip():
            yield Event(kind="summary", text=text.strip(), confidence="summary-derived", **base)
        return

    if etype not in ("user", "assistant"):
        return

    msg = ev.get("message")
    if not isinstance(msg, dict):
        return
    content = msg.get("content")

    if etype == "user":
        if isinstance(content, str):
            text = content.strip()
            if text:
                yield Event(kind="user_text", text=text, **base)
            return
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                itype = item.get("type")
                if itype == "text":
                    text = (item.get("text") or "").strip()
                    if text:
                        yield Event(kind="user_text", text=text, **base)
                elif itype == "tool_result":
                    body = _extract_tool_result_text(item.get("content"))
                    if not body:
                        continue
                    kind, body = _classify_tool_result(body)
                    yield Event(kind=kind, text=body, **base)
        return

    # assistant
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            itype = item.get("type")
            if itype == "text":
                text = (item.get("text") or "").strip()
                if text:
                    yield Event(kind="assistant_text", text=text, **base)
            elif itype == "thinking":
                stats.thinking_blocks_seen += 1
                stats.thinking_blocks_omitted += 1
            elif itype == "tool_use":
                tool_name = item.get("name") or "tool"
                args = item.get("input") or {}
                summary = _summarise_tool_use(tool_name, args)
                yield Event(kind="tool_use", text=summary, **base)


def _extract_tool_result_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                t = item.get("text")
                if isinstance(t, str):
                    parts.append(t)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def _classify_tool_result(body: str) -> tuple[str, str]:
    n = len(body)
    if n <= SHORT_TOOL_RESULT_CHARS:
        return "tool_result_short", body
    if n >= LARGE_TOOL_RESULT_CHARS:
        head = body[:200].replace("\n", " ")
        return "tool_result_metadata", f"[omitted: {n} chars from tool_result; head: {head!r}]"
    if any(p.search(body) for p in TOOL_RESULT_SIGNAL_PATTERNS):
        if n > TOOL_RESULT_SUMMARY_CHARS:
            return "tool_result_summary", body[:TOOL_RESULT_SUMMARY_CHARS] + f"\n[...truncated {n - TOOL_RESULT_SUMMARY_CHARS} chars]"
        return "tool_result_summary", body
    return "tool_result_summary", body[:TOOL_RESULT_SUMMARY_CHARS] + (
        f"\n[...truncated {n - TOOL_RESULT_SUMMARY_CHARS} chars]" if n > TOOL_RESULT_SUMMARY_CHARS else ""
    )


def _summarise_tool_use(name: str, args: dict[str, Any]) -> str:
    intent = ""
    if not isinstance(args, dict):
        return f"[tool_use {name}]"
    for key in ("command", "description", "pattern", "query", "file_path", "path", "url"):
        v = args.get(key)
        if isinstance(v, str) and v.strip():
            snippet = v.strip().replace("\n", " ")
            if len(snippet) > 200:
                snippet = snippet[:200] + "…"
            intent = f"{key}={snippet}"
            break
    return f"[tool_use {name}{(' ' + intent) if intent else ''}]"


# ---------------------------------------------------------------------------
# Redaction & truncation
# ---------------------------------------------------------------------------


def redact(text: str, stats: Stats) -> str:
    out = text
    for pat, repl in SECRET_PATTERNS:
        new, n = pat.subn(repl, out)
        if n:
            label = repl if repl.startswith("[REDACTED") else "[REDACTED:authorization]"
            stats.redactions[label] += n
            out = new
    return out


def truncate_long(text: str, stats: Stats, limit: int = LONG_TEXT_TRUNCATE) -> str:
    if len(text) > limit:
        stats.truncations += 1
        return text[:limit] + f"\n[...truncated {len(text) - limit} chars]"
    return text


def drop_pasted_blocks(text: str, stats: Stats) -> str:
    if len(text) <= PASTED_BLOCK_THRESHOLD:
        return text
    stats.pasted_blocks_omitted += 1
    head = text[:400].replace("\n", " ")
    return f"[omitted: pasted block {len(text)} chars; head: {head!r}]"


def sanitize(text: str, stats: Stats) -> str:
    text = redact(text, stats)
    text = drop_pasted_blocks(text, stats)
    text = truncate_long(text, stats)
    return text


# ---------------------------------------------------------------------------
# Budget allocation
# ---------------------------------------------------------------------------


PRIORITY_ORDER = [
    "user_text",
    "assistant_text",
    "tool_result_short",
    "tool_result_summary",
    "tool_use",
    "tool_result_metadata",
    "summary",
]


def apply_budget(events: list[Event], budget: int, stats: Stats) -> list[Event]:
    main = [e for e in events if not e.is_sidechain and e.source_kind != "sidechain"]
    side = [e for e in events if e.is_sidechain or e.source_kind == "sidechain"]

    sidechain_budget = int(budget * SUBAGENT_BUDGET_FRACTION)
    main_budget = budget - sidechain_budget

    kept_main, used_main = _allocate(main, main_budget, stats, "main")
    kept_side, used_side = _allocate(side, sidechain_budget, stats, "sidechain")

    stats.main_chars_included = used_main
    stats.sidechain_chars_included = used_side
    stats.chars_included = used_main + used_side

    kept = kept_main + kept_side
    kept.sort(key=lambda e: (e.timestamp or "", e.line))
    return kept


def _allocate(events: list[Event], budget: int, stats: Stats, pool_label: str) -> tuple[list[Event], int]:
    by_kind: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        by_kind[e.kind].append(e)
    for kind in by_kind:
        by_kind[kind].sort(key=lambda e: (e.timestamp or "", e.line))

    used = 0
    kept: list[Event] = []
    for kind in PRIORITY_ORDER:
        bucket = by_kind.get(kind, [])
        for e in bucket:
            cost = e.char_len + 80
            if used + cost <= budget:
                kept.append(e)
                used += cost
            else:
                stats.omitted_by_category[f"{pool_label}:{kind}"] += e.char_len
                stats.omitted_events_by_kind[kind] += 1
                if pool_label == "main":
                    stats.main_chars_omitted += e.char_len
                else:
                    stats.sidechain_chars_omitted += e.char_len
    return kept, used


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _short(s: str | None) -> str:
    return (s or "")[:8]


def _ts_short(ts: str | None) -> str:
    if not ts:
        return "????-??-?? ??:??"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts[:16]


def render_evidence(events: list[Event]) -> str:
    by_session: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        by_session[e.session_id].append(e)

    lines: list[str] = []
    lines.append("# Evidence pack\n")
    lines.append(
        "Each event is anchored as `[YYYY-MM-DD HH:MM / sessShort / line:N]`.\n"
        "kinds: user_text, assistant_text, tool_use, tool_result_short, "
        "tool_result_summary, tool_result_metadata, summary.\n"
    )
    for session_id in sorted(by_session.keys(), key=lambda s: (by_session[s][0].timestamp or "", s)):
        ses_events = by_session[session_id]
        ses_events.sort(key=lambda e: (e.timestamp or "", e.line))
        first = ses_events[0]
        lines.append(f"\n## Session {first.session_short} ({session_id})\n")
        lines.append(
            f"source={first.source_kind} sidechain={first.is_sidechain} "
            f"branch={first.git_branch or '?'} cwd={first.cwd or '?'}\n"
        )
        for e in ses_events:
            anchor = f"[{_ts_short(e.timestamp)} / {e.session_short} / line:{e.line}]"
            tag = f"**{e.kind}**"
            if e.confidence != "direct":
                tag += f" *(confidence: {e.confidence})*"
            if e.is_sidechain:
                tag += " *(sidechain)*"
            lines.append(f"\n### {anchor} {tag}\n")
            lines.append(e.text.rstrip() + "\n")
    return "".join(lines)


def render_source_map(events: list[Event]) -> dict[str, Any]:
    return {
        "events": [
            {
                "session_short": e.session_short,
                "session_id": e.session_id,
                "uuid": e.uuid,
                "parent_uuid": e.parent_uuid,
                "line": e.line,
                "timestamp": e.timestamp,
                "git_branch": e.git_branch,
                "cwd": e.cwd,
                "kind": e.kind,
                "is_sidechain": e.is_sidechain,
                "source_kind": e.source_kind,
                "confidence": e.confidence,
            }
            for e in events
        ]
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(project_root: Path, budget_chars: int, output_dir: Path | None = None) -> dict[str, Any]:
    """Run the full extraction pipeline.

    Returns a dict with status + (on ok) evidence_md inline, source_map, stats.
    If `output_dir` is given, also writes evidence.md/source-map.json/stats.json
    there for debug. By default everything is returned inline — no files touched.
    """
    stats = Stats(budget_chars=budget_chars)

    sessions = discover_sessions(project_root, stats)
    if not sessions:
        return {
            "status": "no_sessions",
            "message": (
                "No Claude Code sessions found for this project. Run /retro again "
                "after using Claude Code in this repository."
            ),
            "project_root": str(project_root),
            "stats": stats.to_json(),
        }

    all_events: list[Event] = []
    for sf in sessions:
        for ev in parse_session(sf, stats):
            ev.text = sanitize(ev.text, stats)
            stats.events_by_kind[ev.kind] += 1
            stats.chars_total_raw += ev.char_len
            ts = ev.timestamp
            if ts:
                stats.date_min = ts if (stats.date_min is None or ts < stats.date_min) else stats.date_min
                stats.date_max = ts if (stats.date_max is None or ts > stats.date_max) else stats.date_max
            all_events.append(ev)

    kept = apply_budget(all_events, budget_chars, stats)
    stats.estimated_tokens_included = int(stats.chars_included * TOKEN_PER_CHAR)

    evidence_md = render_evidence(kept)
    source_map = render_source_map(kept)
    stats_json = stats.to_json()

    result: dict[str, Any] = {
        "status": "ok",
        "project_root": str(project_root),
        "sessions_total": stats.sessions_accepted,
        "events_kept": len(kept),
        "date_min": stats.date_min,
        "date_max": stats.date_max,
        "evidence_md": evidence_md,
        "source_map": source_map,
        "stats": stats_json,
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "evidence.md").write_text(evidence_md, encoding="utf-8")
        (output_dir / "source-map.json").write_text(
            json.dumps(source_map, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output_dir / "stats.json").write_text(
            json.dumps(stats_json, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        result["evidence_path"] = str(output_dir / "evidence.md")
        result["source_map_path"] = str(output_dir / "source-map.json")
        result["stats_path"] = str(output_dir / "stats.json")

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract Claude Code sessions for /retro.")
    parser.add_argument("--project-root", help="Project root path. Defaults to cwd.")
    parser.add_argument(
        "--output-dir",
        help="Optional. If given, also writes evidence.md/source-map.json/stats.json into it. "
        "Default behavior is stdout-only — no files touched.",
    )
    parser.add_argument("--budget-chars", type=int, default=DEFAULT_BUDGET_CHARS)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    start = Path(args.project_root).resolve() if args.project_root else Path.cwd().resolve()
    root, err = resolve_project_root(start)
    if root is None:
        print(json.dumps({"status": "fail", "error": err}, ensure_ascii=False))
        return 2

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    result = run(root, args.budget_chars, output_dir=output_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
