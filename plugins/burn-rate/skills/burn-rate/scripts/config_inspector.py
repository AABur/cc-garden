# config_inspector.py
"""Inventory Claude Code config: tool-search state, hooks, skills, MCP, plugins,
CLAUDE.md sizes. Read-only."""
from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

_TOP_LEVEL_KEY = re.compile(r"^[A-Za-z_][\w-]*:")

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
    skill_description_tokens: int = 0
    plugin_description_tokens: int = 0
    plugin_count: int = 0
    description_weight_by_plugin: dict = field(default_factory=dict)  # plugin -> approx tokens


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


def extract_description(text: str) -> str:
    """Extract the `description:` value from SKILL.md YAML frontmatter using
    stdlib only (no yaml dep). Handles inline values, folded `>-`/`|` block
    scalars, and multi-line plain scalars. Returns "" if absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    # Frontmatter is everything up to the next standalone "---".
    fm = []
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        fm.append(ln)
    # Locate the description: key line and its indentation.
    for i, ln in enumerate(fm):
        stripped = ln.lstrip()
        if not stripped.startswith("description:"):
            continue
        key_indent = len(ln) - len(stripped)
        inline = stripped[len("description:"):].strip()
        # Strip a leading block-scalar indicator (>- , >, |, |- , etc.).
        if inline and inline[0] in "|>":
            inline = ""
        parts = [inline] if inline else []
        # Capture following lines more indented than the key (continuation).
        for cont in fm[i + 1:]:
            if not cont.strip():
                parts.append("")
                continue
            cont_indent = len(cont) - len(cont.lstrip())
            if cont_indent <= key_indent and _TOP_LEVEL_KEY.match(cont.strip()):
                break
            if cont_indent <= key_indent:
                break
            parts.append(cont.strip())
        return " ".join(p for p in parts if p).strip()
    return ""


def measure_descriptions(cache_dir: Path) -> dict:
    """Walk the plugin cache and approximate the per-turn token cost of skill and
    plugin descriptions. Defensive: unreadable/missing files contribute 0.

    Plugin name is the path segment two levels under cache (cache/<marketplace>/<plugin>/...).
    """
    result = {
        "skill_description_tokens": 0,
        "plugin_description_tokens": 0,
        "plugin_count": 0,
        "description_weight_by_plugin": {},
    }
    if not cache_dir.exists():
        return result
    weights = result["description_weight_by_plugin"]
    plugins_seen = set()

    def _plugin_name(path: Path) -> str:
        try:
            rel = path.relative_to(cache_dir).parts
        except ValueError:
            return ""
        return rel[1] if len(rel) >= 2 else ""

    for skill_md in cache_dir.rglob("SKILL.md"):
        plugin = _plugin_name(skill_md)
        if plugin:
            plugins_seen.add(plugin)
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        desc = extract_description(text)
        tokens = len(desc) // 4
        if tokens:
            result["skill_description_tokens"] += tokens
            if plugin:
                weights[plugin] = weights.get(plugin, 0) + tokens

    for plugin_json in cache_dir.rglob("plugin.json"):
        if plugin_json.parent.name != ".claude-plugin":
            continue
        plugin = _plugin_name(plugin_json)
        if plugin:
            plugins_seen.add(plugin)
        data = _load(plugin_json)
        if not isinstance(data, dict):
            continue
        desc = data.get("description")
        if not isinstance(desc, str):
            continue
        tokens = len(desc) // 4
        if tokens:
            result["plugin_description_tokens"] += tokens
            if plugin:
                weights[plugin] = weights.get(plugin, 0) + tokens

    result["plugin_count"] = len(plugins_seen)
    return result


def build_snapshot() -> ConfigSnapshot:
    user_settings = _load(CLAUDE_DIR / "settings.json") or {}
    proj_settings = _load(Path.cwd() / ".claude" / "settings.json") or {}
    env = {**(user_settings.get("env") or {}), **(proj_settings.get("env") or {})}
    ts_on, ts_mode = detect_tool_search(env, dict(os.environ))
    hooks = read_hooks(user_settings, "global") + read_hooks(proj_settings, "project")
    plugins = list(user_settings.get("enabledPlugins") or [])
    mcp = sorted((user_settings.get("mcpServers") or {}).keys())
    cache_dir = CLAUDE_DIR / "plugins" / "cache"
    skill_count = sum(1 for _ in cache_dir.rglob("SKILL.md")) if cache_dir.exists() else 0
    cmd_tokens = {}
    for p in (CLAUDE_DIR / "CLAUDE.md", Path.cwd() / "CLAUDE.md"):
        if p.exists():
            cmd_tokens[str(p)] = approx_tokens(p)
    desc = measure_descriptions(cache_dir)
    return ConfigSnapshot(
        ts_on, ts_mode, hooks, mcp, plugins, skill_count, cmd_tokens,
        skill_description_tokens=desc["skill_description_tokens"],
        plugin_description_tokens=desc["plugin_description_tokens"],
        plugin_count=desc["plugin_count"],
        description_weight_by_plugin=desc["description_weight_by_plugin"],
    )
