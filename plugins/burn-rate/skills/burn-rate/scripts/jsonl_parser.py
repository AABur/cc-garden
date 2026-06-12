# jsonl_parser.py
"""Parse ~/.claude/projects/**/*.jsonl into deduped, attribution-aware sessions.
All analysis is local; payload content is inspected to extract names/sizes but is
never persisted or emitted."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0

    @property
    def context_size(self) -> int:
        return (self.input_tokens + self.cache_read_tokens
                + self.cache_write_5m_tokens + self.cache_write_1h_tokens)


@dataclass
class Turn:
    uuid: str
    message_id: str
    request_id: str
    session_id: str
    cwd: str
    timestamp: Optional[datetime]
    model: Optional[str]
    usage: Optional[Usage]
    is_sidechain: bool = False
    session_kind: Optional[str] = None
    api_error_status: Optional[str] = None
    service_tier: Optional[str] = None
    attribution_skill: Optional[str] = None
    attribution_plugin: Optional[str] = None
    attribution_mcp: Optional[str] = None
    attribution_agent: Optional[str] = None
    tool_calls: list = field(default_factory=list)
    text_chars: int = 0

    @property
    def dedup_key(self) -> tuple:
        return (self.message_id or self.uuid, self.request_id)


@dataclass
class Session:
    session_id: str
    cwd: str = ""
    turns: list = field(default_factory=list)
    total_usage: Usage = field(default_factory=Usage)
    models_used: dict = field(default_factory=dict)
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None

    @property
    def deduped_turn_count(self) -> int:
        return len(self.turns)

    @property
    def project(self) -> str:
        return Path(self.cwd).name if self.cwd else "unknown"


@dataclass
class ParseStats:
    raw_assistant_records: int = 0
    deduped_assistant_requests: int = 0
    duplicates_removed: int = 0
    sidechain_assistant_records: int = 0
    user_tool_events: int = 0
    hook_events: int = 0
    total_parsed_events: int = 0


def _ts(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    # Make tz-aware: transcripts without an offset would otherwise yield naive
    # datetimes that raise TypeError when compared with the aware `since` cutoff,
    # silently dropping the whole file. Non-UTC offsets are left as-is; comparison
    # against `since` (which is UTC-aware) works correctly for any tz-aware value.
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_turn(raw: dict) -> Optional[Turn]:
    if raw.get("type") != "assistant":
        return None
    msg = raw.get("message", {})
    if not isinstance(msg, dict):
        return None
    u = msg.get("usage")
    u = u if isinstance(u, dict) else {}
    cc = u.get("cache_creation")
    if isinstance(cc, dict):
        c5 = int(cc.get("ephemeral_5m_input_tokens", 0) or 0)
        c1 = int(cc.get("ephemeral_1h_input_tokens", 0) or 0)
    else:  # fallback: no split available -> attribute all to 5m
        c5 = int(u.get("cache_creation_input_tokens", 0) or 0)
        c1 = 0
    usage = Usage(
        input_tokens=int(u.get("input_tokens", 0) or 0),
        output_tokens=int(u.get("output_tokens", 0) or 0),
        cache_read_tokens=int(u.get("cache_read_input_tokens", 0) or 0),
        cache_write_5m_tokens=c5, cache_write_1h_tokens=c1,
    )
    tool_calls, text_chars = [], 0
    for item in msg.get("content", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "tool_use":
            tool_calls.append(item.get("name", ""))
        elif item.get("type") == "text":
            text_chars += len(item.get("text", "") or "")
    return Turn(
        uuid=raw.get("uuid", ""), message_id=msg.get("id", "") or "",
        request_id=raw.get("requestId", "") or "", session_id=raw.get("sessionId", ""),
        cwd=raw.get("cwd", ""), timestamp=_ts(raw.get("timestamp")),
        model=msg.get("model"), usage=usage,
        is_sidechain=bool(raw.get("isSidechain", False)),
        session_kind=raw.get("sessionKind"), api_error_status=raw.get("apiErrorStatus"),
        service_tier=u.get("service_tier"),
        attribution_skill=raw.get("attributionSkill"),
        attribution_plugin=raw.get("attributionPlugin"),
        attribution_mcp=raw.get("attributionMcpServer"),
        attribution_agent=raw.get("attributionAgent"),
        tool_calls=tool_calls, text_chars=text_chars,
    )


def build_session_from_records(session_id: str, records: list) -> tuple:
    """Return (session, stats) where stats is a ParseStats populated from records."""
    sess = Session(session_id=session_id)
    stats = ParseStats()
    seen = set()
    for raw in records:
        rec_type = raw.get("type")
        if rec_type == "user":
            stats.user_tool_events += 1
            continue
        if rec_type != "assistant":
            continue
        stats.raw_assistant_records += 1
        if bool(raw.get("isSidechain", False)):
            stats.sidechain_assistant_records += 1
        turn = parse_turn(raw)
        if turn is None:
            continue
        if turn.dedup_key in seen:
            continue
        seen.add(turn.dedup_key)
        stats.deduped_assistant_requests += 1
        if not sess.cwd and turn.cwd:
            sess.cwd = turn.cwd
        sess.turns.append(turn)
        if turn.usage:
            u, t = sess.total_usage, turn.usage
            u.input_tokens += t.input_tokens
            u.output_tokens += t.output_tokens
            u.cache_read_tokens += t.cache_read_tokens
            u.cache_write_5m_tokens += t.cache_write_5m_tokens
            u.cache_write_1h_tokens += t.cache_write_1h_tokens
        if turn.model:
            sess.models_used[turn.model] = sess.models_used.get(turn.model, 0) + 1
        if turn.timestamp:
            if sess.first_timestamp is None or turn.timestamp < sess.first_timestamp:
                sess.first_timestamp = turn.timestamp
            if sess.last_timestamp is None or turn.timestamp > sess.last_timestamp:
                sess.last_timestamp = turn.timestamp
    stats.duplicates_removed = stats.raw_assistant_records - stats.deduped_assistant_requests
    stats.total_parsed_events = stats.raw_assistant_records + stats.user_tool_events + stats.hook_events
    return sess, stats


def parse_session_file(path: Path, since: Optional[datetime]) -> tuple:
    """Return (session, stats, bad_lines).

    bad_lines counts JSON lines that failed to parse — surfaced upstream so a
    partially-corrupt transcript is not silently counted as complete.
    stats is a ParseStats populated from the records in this file.
    """
    records = []
    bad_lines = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                bad_lines += 1
                continue
            if not isinstance(raw, dict):
                bad_lines += 1
                continue
            if since is not None:
                ts = _ts(raw.get("timestamp"))
                if not ts or ts < since:
                    continue
            records.append(raw)
    sess, stats = build_session_from_records(path.stem, records)
    return sess, stats, bad_lines


def parse_all(projects_dir: Path = Path.home() / ".claude" / "projects",
              since_days: int = 7) -> tuple:
    """Return (sessions, causal_events, stats, errors).

    causal_events is a placeholder list (populated in a later step).
    stats is an aggregate ParseStats summed across all files.
    errors lists transcripts that were skipped or partially unreadable, so the
    audit can surface that its numbers were computed over an incomplete dataset
    rather than reporting silently truncated totals.
    """
    if not projects_dir.exists():
        return [], [], ParseStats(), []
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    cutoff = since.timestamp()
    sessions, errors = [], []
    aggregate = ParseStats()
    for p in projects_dir.rglob("*.jsonl"):
        try:
            if p.stat().st_mtime < cutoff:
                continue
            sess, stats, bad_lines = parse_session_file(p, since=since)
            aggregate.raw_assistant_records += stats.raw_assistant_records
            aggregate.deduped_assistant_requests += stats.deduped_assistant_requests
            aggregate.duplicates_removed += stats.duplicates_removed
            aggregate.sidechain_assistant_records += stats.sidechain_assistant_records
            aggregate.user_tool_events += stats.user_tool_events
            aggregate.hook_events += stats.hook_events
            aggregate.total_parsed_events += stats.total_parsed_events
            if bad_lines:
                errors.append(f"{p.name}: {bad_lines} unparseable line(s)")
            if sess.deduped_turn_count > 0:
                sessions.append(sess)
        except OSError as e:
            # Expected, benign-to-skip (permissions, races) — record briefly.
            errors.append(f"{p.name}: {type(e).__name__}")
        except Exception as e:
            # A bug in parsing must not abort the audit, but must be surfaced —
            # not blanket-swallowed — so wrong totals don't look complete.
            errors.append(f"{p.name}: {type(e).__name__}: {e}")
    return sessions, [], aggregate, errors
