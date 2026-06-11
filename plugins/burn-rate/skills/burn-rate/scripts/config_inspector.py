# config_inspector.py
"""Inventory Claude Code config: tool-search state, hooks, skills, MCP, plugins,
CLAUDE.md sizes. Read-only."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"


@dataclass
class ConfigSnapshot:
    tool_search_enabled: bool
    tool_search_mode: str
    hooks: list = field(default_factory=list)
    mcp_servers: list = field(default_factory=list)
    plugins: list = field(default_factory=list)
    skill_count: int = 0
    claude_md_tokens: dict = field(default_factory=dict)  # path -> approx tokens


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def detect_tool_search(settings_env: dict, process_env: dict) -> tuple:
    raw = str(process_env.get("ENABLE_TOOL_SEARCH")
              or settings_env.get("ENABLE_TOOL_SEARCH") or "").strip()
    if not raw:
        return True, "default"
    if raw.lower() in ("false", "0", "off", "no", "disabled"):
        return False, raw
    return True, raw


def read_hooks(settings: dict, scope: str) -> list:
    out = []
    for event, groups in (settings.get("hooks") or {}).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for hook in group.get("hooks", []) or []:
                if not isinstance(hook, dict):
                    continue
                out.append({"event": event, "command": hook.get("command", ""), "scope": scope})
    return out


def approx_tokens(path: Path) -> int:
    try:
        return path.stat().st_size // 4
    except OSError:
        return 0


def build_snapshot() -> ConfigSnapshot:
    user_settings = _load(CLAUDE_DIR / "settings.json") or {}
    proj_settings = _load(Path.cwd() / ".claude" / "settings.json") or {}
    env = {**(user_settings.get("env") or {}), **(proj_settings.get("env") or {})}
    ts_on, ts_mode = detect_tool_search(env, dict(os.environ))
    hooks = read_hooks(user_settings, "global") + read_hooks(proj_settings, "project")
    plugins = list(user_settings.get("enabledPlugins") or [])
    mcp = sorted((user_settings.get("mcpServers") or {}).keys())
    skill_count = sum(1 for _ in (CLAUDE_DIR / "plugins" / "cache").rglob("SKILL.md")) \
        if (CLAUDE_DIR / "plugins" / "cache").exists() else 0
    cmd_tokens = {}
    for p in (CLAUDE_DIR / "CLAUDE.md", Path.cwd() / "CLAUDE.md"):
        if p.exists():
            cmd_tokens[str(p)] = approx_tokens(p)
    return ConfigSnapshot(ts_on, ts_mode, hooks, mcp, plugins, skill_count, cmd_tokens)
