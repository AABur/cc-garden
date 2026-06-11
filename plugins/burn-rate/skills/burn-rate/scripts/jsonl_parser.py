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
    deduped_turn_count: int = 0
    models_used: dict = field(default_factory=dict)
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None

    @property
    def project(self) -> str:
        return Path(self.cwd).name if self.cwd else "unknown"


def _ts(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    # Normalize to tz-aware UTC: transcripts without an offset would otherwise
    # yield naive datetimes that raise TypeError when compared with the aware
    # `since` cutoff, silently dropping the whole file.
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


def build_session_from_records(session_id: str, records: list) -> Session:
    sess = Session(session_id=session_id)
    seen = set()
    for raw in records:
        turn = parse_turn(raw)
        if turn is None:
            continue
        if turn.dedup_key in seen:
            continue
        seen.add(turn.dedup_key)
        if not sess.cwd and turn.cwd:
            sess.cwd = turn.cwd
        sess.turns.append(turn)
        sess.deduped_turn_count += 1
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
    return sess


def parse_session_file(path: Path, since: Optional[datetime]) -> Session:
    records = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since is not None:
                ts = _ts(raw.get("timestamp"))
                if not ts or ts < since:
                    continue
            records.append(raw)
    sess = build_session_from_records(path.stem, records)
    return sess


def parse_all(projects_dir: Path = Path.home() / ".claude" / "projects",
              since_days: int = 7) -> list:
    if not projects_dir.exists():
        return []
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    cutoff = since.timestamp()
    sessions = []
    for p in projects_dir.rglob("*.jsonl"):
        try:
            if p.stat().st_mtime < cutoff:
                continue
            sess = parse_session_file(p, since=since)
            if sess.deduped_turn_count > 0:
                sessions.append(sess)
        except Exception:
            # One malformed/unreadable transcript must not abort the whole audit.
            continue
    return sessions
