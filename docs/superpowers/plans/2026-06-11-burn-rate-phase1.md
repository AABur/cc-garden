# burn-rate Phase 1 (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a read-only, chat-only Claude Code token-spend auditor (`burn-rate`) with deduplicated, attribution-aware transcript analysis, a current 2026 price model, and 4 core leak detectors — registered in the `cc-garden` marketplace and runnable via `audit.py --days 7`.

**Architecture:** Python stdlib only. `audit.py` orchestrates: `ccusage.py` (baseline $), `jsonl_parser.py` (deduped transcript parse with rich attribution + 5m/1h cache split), `config_inspector.py` (config inventory), `attribution.py` (Pareto), and `detectors/*` (leaks). Output is JSON to stdout; the SKILL.md body narrates in the user's language. No writes, no network except the optional `ccusage` call.

**Tech Stack:** Python 3.11+ stdlib (`json`, `dataclasses`, `pathlib`, `subprocess`, `unittest`), `ccusage` via `npx` (optional), Claude Code plugin/marketplace manifests.

**Spec:** `docs/superpowers/specs/2026-06-11-burn-rate-design.md`
**Branch:** `feat/burn-rate`

---

## File Structure

```
plugins/burn-rate/
├── .claude-plugin/plugin.json
├── LICENSE
├── README.md
└── skills/burn-rate/
    ├── SKILL.md
    ├── scripts/
    │   ├── pricing.py            + test_pricing.py
    │   ├── jsonl_parser.py       + test_jsonl_parser.py
    │   ├── ccusage.py            + test_ccusage.py
    │   ├── config_inspector.py   + test_config_inspector.py
    │   ├── attribution.py        + test_attribution.py
    │   ├── detectors/
    │   │   ├── __init__.py        (Leak dataclass + registry)
    │   │   ├── model_selection.py + test_model_selection.py
    │   │   ├── context_rot.py     + test_context_rot.py
    │   │   ├── cache.py           + test_cache.py
    │   │   └── claude_md_bloat.py + test_claude_md_bloat.py
    │   └── audit.py              + test_audit.py
    └── references/{leak-taxonomy.md, pricing-2026.md, techniques.md}  (Phase 1: stubs ok, expanded later)
```

**Test convention (repo standard):** stdlib `unittest`, `test_*.py` beside source, runnable standalone (`python3 test_x.py`) and pytest-discoverable. Run each test file directly.

---

## Task 1: Scaffolding & marketplace registration

**Files:**
- Create: `plugins/burn-rate/.claude-plugin/plugin.json`
- Create: `plugins/burn-rate/LICENSE`
- Modify: `.claude-plugin/marketplace.json` (append burn-rate entry)

- [ ] **Step 1: Create plugin.json**

```json
{
  "name": "burn-rate",
  "description": "Audit Claude Code token spend, read-only, and rank where tokens are leaking. Deduplicated transcript analysis with skill/plugin/MCP/agent attribution, current 2026 pricing, and concrete fixes — no config is ever modified.",
  "author": {
    "name": "Alexander Burchenko",
    "email": "aabur@mail.ru"
  }
}
```

- [ ] **Step 2: Create LICENSE (MIT, dual copyright)**

```
MIT License

Copyright (c) 2026 Bayram Annakov (original token-audit concept and leak taxonomy)
Copyright (c) 2026 Alexander Burchenko (burn-rate implementation)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Register in marketplace.json**

Append this object to the `plugins` array in `.claude-plugin/marketplace.json` (after the `lucky-break` entry):

```json
    {
      "name": "burn-rate",
      "description": "Audit Claude Code token spend, read-only, and rank where tokens are leaking. Deduplicated transcript analysis with skill/plugin/MCP/agent attribution, current 2026 pricing, and concrete fixes — no config is ever modified.",
      "author": {
        "name": "Alexander Burchenko",
        "email": "aabur@mail.ru"
      },
      "source": "./plugins/burn-rate"
    }
```

- [ ] **Step 4: Validate JSON**

Run: `python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); json.load(open('plugins/burn-rate/.claude-plugin/plugin.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/.claude-plugin/plugin.json plugins/burn-rate/LICENSE .claude-plugin/marketplace.json
git commit -m "feat: scaffold burn-rate plugin and register in marketplace"
```

---

## Task 2: pricing.py — 2026 price model

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/pricing.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_pricing.py`

**Price table (per million tokens, 2026 snapshot; source: Anthropic `claude-api` skill, cached 2026-06-04):**

| family | input | output | cache_write_5m | cache_write_1h | cache_read | cacheable_min |
|---|---|---|---|---|---|---|
| opus (4.x) | 5 | 25 | 6.25 | 10 | 0.5 | 4096 |
| sonnet (4.6) | 3 | 15 | 3.75 | 6 | 0.3 | 2048 |
| haiku (4.5) | 1 | 5 | 1.25 | 2 | 0.1 | 4096 |
| fable-5 | 10 | 50 | 12.5 | 20 | 1.0 | 2048 |

- [ ] **Step 1: Write the failing test**

```python
# test_pricing.py
import unittest
import pricing


class TestPricing(unittest.TestCase):
    def test_resolve_known_families(self):
        self.assertEqual(pricing.resolve_family("claude-opus-4-8"), "opus")
        self.assertEqual(pricing.resolve_family("claude-sonnet-4-6"), "sonnet")
        self.assertEqual(pricing.resolve_family("claude-haiku-4-5-20251001"), "haiku")
        self.assertEqual(pricing.resolve_family("claude-fable-5"), "fable")

    def test_synthetic_and_unknown_are_not_opus(self):
        self.assertEqual(pricing.resolve_family("<synthetic>"), "synthetic")
        self.assertIsNone(pricing.resolve_family("gpt-5.4"))
        self.assertIsNone(pricing.resolve_family(None))

    def test_estimate_cost_per_bucket(self):
        b = pricing.TokenBreakdown(
            input_tokens=1_000_000, output_tokens=1_000_000,
            cache_write_5m_tokens=1_000_000, cache_write_1h_tokens=1_000_000,
            cache_read_tokens=1_000_000,
        )
        # opus: 5 + 25 + 6.25 + 10 + 0.5 = 46.75
        self.assertAlmostEqual(pricing.estimate_cost(b, "claude-opus-4-8"), 46.75, places=2)

    def test_synthetic_costs_zero(self):
        b = pricing.TokenBreakdown(input_tokens=1_000_000)
        self.assertEqual(pricing.estimate_cost(b, "<synthetic>"), 0.0)

    def test_unknown_costs_zero_and_flagged(self):
        b = pricing.TokenBreakdown(input_tokens=1_000_000)
        self.assertEqual(pricing.estimate_cost(b, "gpt-5.4"), 0.0)

    def test_cacheable_minimum(self):
        self.assertEqual(pricing.cacheable_minimum("claude-opus-4-8"), 4096)
        self.assertEqual(pricing.cacheable_minimum("claude-sonnet-4-6"), 2048)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/burn-rate/skills/burn-rate/scripts && python3 test_pricing.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'pricing'`

- [ ] **Step 3: Write minimal implementation**

```python
# pricing.py
"""2026 price model for Claude Code token usage. Snapshot — see references/pricing-2026.md.

Prices are USD per million tokens. Unknown/non-Claude models cost 0 (we do not
guess), and synthetic turns cost 0. ccusage remains the authority for the spend
baseline; this table only powers per-leak detector estimates.
"""
from __future__ import annotations
from dataclasses import dataclass

# family -> per-million rates + cacheable minimum (tokens)
PRICING = {
    "opus":   {"input": 5.0,  "output": 25.0, "cw5m": 6.25,  "cw1h": 10.0, "cr": 0.5, "min": 4096},
    "sonnet": {"input": 3.0,  "output": 15.0, "cw5m": 3.75,  "cw1h": 6.0,  "cr": 0.3, "min": 2048},
    "haiku":  {"input": 1.0,  "output": 5.0,  "cw5m": 1.25,  "cw1h": 2.0,  "cr": 0.1, "min": 4096},
    "fable":  {"input": 10.0, "output": 50.0, "cw5m": 12.5,  "cw1h": 20.0, "cr": 1.0, "min": 2048},
}
SNAPSHOT_DATE = "2026-06-04"


@dataclass
class TokenBreakdown:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total(self) -> int:
        return (self.input_tokens + self.output_tokens + self.cache_write_5m_tokens
                + self.cache_write_1h_tokens + self.cache_read_tokens)


def resolve_family(model: str | None) -> str | None:
    """Map a model ID to a pricing family. Returns 'synthetic' for synthetic
    turns, None for non-Claude/unknown (which we refuse to price)."""
    if not model:
        return None
    m = model.lower()
    if m == "<synthetic>":
        return "synthetic"
    if m.startswith("claude-opus-4"):
        return "opus"
    if m.startswith("claude-sonnet-4"):
        return "sonnet"
    if m.startswith("claude-haiku-4"):
        return "haiku"
    if m.startswith("claude-fable-5") or m.startswith("claude-mythos-5"):
        return "fable"
    return None


def estimate_cost(b: TokenBreakdown, model: str | None) -> float:
    fam = resolve_family(model)
    if fam in (None, "synthetic"):
        return 0.0
    p = PRICING[fam]
    cost = (b.input_tokens * p["input"] + b.output_tokens * p["output"]
            + b.cache_write_5m_tokens * p["cw5m"] + b.cache_write_1h_tokens * p["cw1h"]
            + b.cache_read_tokens * p["cr"]) / 1_000_000
    return round(cost, 6)


def cacheable_minimum(model: str | None) -> int | None:
    fam = resolve_family(model)
    if fam in (None, "synthetic"):
        return None
    return PRICING[fam]["min"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_pricing.py`
Expected: `OK` (6 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/pricing.py plugins/burn-rate/skills/burn-rate/scripts/test_pricing.py
git commit -m "feat: add burn-rate 2026 pricing model"
```

---

## Task 3: jsonl_parser.py — deduped, attribution-aware parser

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/jsonl_parser.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_jsonl_parser.py`

Key behaviors: split `cache_creation` into 5m/1h; dedup on `(message.id, requestId)`; capture attribution fields; two-stage time filter is handled at the `parse_all` level (Task tested with explicit JSONL fixtures).

- [ ] **Step 1: Write the failing test**

```python
# test_jsonl_parser.py
import io
import unittest
import jsonl_parser as jp


def _assistant_line(uuid, msg_id, req_id, model="claude-opus-4-8",
                    cr=0, c5=0, c1=0, out=10, inp=5, sidechain=False,
                    skill=None, plugin=None, mcp=None, agent=None, kind=None, err=None):
    return {
        "type": "assistant", "uuid": uuid, "requestId": req_id,
        "sessionId": "s1", "cwd": "/tmp/proj", "timestamp": "2026-06-10T00:00:00Z",
        "isSidechain": sidechain, "sessionKind": kind, "apiErrorStatus": err,
        "attributionSkill": skill, "attributionPlugin": plugin,
        "attributionMcpServer": mcp, "attributionAgent": agent,
        "message": {
            "id": msg_id, "model": model, "role": "assistant", "content": [],
            "usage": {
                "input_tokens": inp, "output_tokens": out,
                "cache_read_input_tokens": cr,
                "cache_creation": {"ephemeral_5m_input_tokens": c5, "ephemeral_1h_input_tokens": c1},
                "cache_creation_input_tokens": c5 + c1, "service_tier": "standard",
            },
        },
    }


class TestParser(unittest.TestCase):
    def test_cache_split(self):
        t = jp.parse_turn(_assistant_line("u1", "m1", "r1", c5=100, c1=200))
        self.assertEqual(t.usage.cache_write_5m_tokens, 100)
        self.assertEqual(t.usage.cache_write_1h_tokens, 200)

    def test_attribution_extracted(self):
        t = jp.parse_turn(_assistant_line("u1", "m1", "r1", skill="superpowers:brainstorming",
                                          plugin="superpowers", sidechain=True, err="429"))
        self.assertEqual(t.attribution_skill, "superpowers:brainstorming")
        self.assertEqual(t.attribution_plugin, "superpowers")
        self.assertTrue(t.is_sidechain)
        self.assertEqual(t.api_error_status, "429")

    def test_dedup_by_message_and_request_id(self):
        # Same (message.id, requestId) appears twice (resume/branch) -> counted once.
        lines = [_assistant_line("u1", "m1", "r1", out=10),
                 _assistant_line("u2", "m1", "r1", out=10),
                 _assistant_line("u3", "m2", "r2", out=10)]
        sess = jp.build_session_from_records("s1", lines)
        self.assertEqual(sess.total_usage.output_tokens, 20)  # 2 unique, not 3
        self.assertEqual(sess.deduped_turn_count, 2)

    def test_synthetic_model_preserved(self):
        t = jp.parse_turn(_assistant_line("u1", "m1", "r1", model="<synthetic>"))
        self.assertEqual(t.model, "<synthetic>")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_jsonl_parser.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'jsonl_parser'`

- [ ] **Step 3: Write minimal implementation**

```python
# jsonl_parser.py
"""Parse ~/.claude/projects/**/*.jsonl into deduped, attribution-aware sessions.
All analysis is local; only sizes/counts/names are retained — never payloads."""
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
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def parse_turn(raw: dict) -> Optional[Turn]:
    if raw.get("type") != "assistant":
        return None
    msg = raw.get("message", {}) or {}
    u = msg.get("usage", {}) or {}
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
                if ts and ts < since:
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
        except OSError:
            continue
    return sessions
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_jsonl_parser.py`
Expected: `OK` (4 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/jsonl_parser.py plugins/burn-rate/skills/burn-rate/scripts/test_jsonl_parser.py
git commit -m "feat: add deduped attribution-aware jsonl parser"
```

---

## Task 4: ccusage.py — baseline wrapper

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/ccusage.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_ccusage.py`

- [ ] **Step 1: Write the failing test**

```python
# test_ccusage.py
import json
import unittest
from unittest import mock
import ccusage


class TestCcusage(unittest.TestCase):
    def test_parses_json_on_success(self):
        fake = json.dumps({"daily": [{"date": "2026-06-10", "totalCost": 1.23}]})
        with mock.patch.object(ccusage, "_run", return_value=(0, fake, "")):
            data, err = ccusage.run_daily(days=7)
        self.assertIsNone(err)
        self.assertEqual(data["daily"][0]["totalCost"], 1.23)

    def test_graceful_when_missing(self):
        with mock.patch.object(ccusage, "_run", return_value=(127, "", "not found")):
            data, err = ccusage.run_daily(days=7)
        self.assertIsNone(data)
        self.assertIn("ccusage", err.lower())

    def test_graceful_on_bad_json(self):
        with mock.patch.object(ccusage, "_run", return_value=(0, "not json", "")):
            data, err = ccusage.run_daily(days=7)
        self.assertIsNone(data)
        self.assertIn("parse", err.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_ccusage.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'ccusage'`

- [ ] **Step 3: Write minimal implementation**

```python
# ccusage.py
"""Thin wrapper around the ccusage CLI for the spend baseline.

Runs in online `auto` mode (fresh LiteLLM prices + dedup). Best-effort: if Node
or ccusage is missing, returns (None, error) and the audit proceeds without it.
"""
from __future__ import annotations
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

_CCUSAGE_VERSION = os.environ.get("CCUSAGE_VERSION", "20.0.11")


def _run(args: list, timeout: int = 180) -> tuple:
    try:
        proc = subprocess.run(["npx", "-y", f"ccusage@{_CCUSAGE_VERSION}", *args],
                              capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "npx/node not found"
    except subprocess.TimeoutExpired:
        return 124, "", "ccusage timed out"


def run_daily(days: int = 7) -> tuple:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y%m%d")
    until = now.strftime("%Y%m%d")
    rc, out, err = _run(["daily", f"--since={since}", f"--until={until}", "--json"])
    if rc != 0:
        return None, f"ccusage unavailable: {(err or 'failed').strip()}"
    try:
        return json.loads(out), None
    except json.JSONDecodeError as e:
        return None, f"ccusage JSON parse failed: {e}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_ccusage.py`
Expected: `OK` (3 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/ccusage.py plugins/burn-rate/skills/burn-rate/scripts/test_ccusage.py
git commit -m "feat: add ccusage baseline wrapper with graceful fallback"
```

---

## Task 5: config_inspector.py — config inventory

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/config_inspector.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_config_inspector.py`

- [ ] **Step 1: Write the failing test**

```python
# test_config_inspector.py
import json
import tempfile
import unittest
from pathlib import Path
import config_inspector as ci


class TestConfigInspector(unittest.TestCase):
    def test_tool_search_default_on(self):
        self.assertEqual(ci.detect_tool_search({}, {}), (True, "default"))

    def test_tool_search_explicit_off(self):
        self.assertEqual(ci.detect_tool_search({"ENABLE_TOOL_SEARCH": "false"}, {}),
                         (False, "false"))

    def test_count_hooks(self):
        settings = {"hooks": {"SessionStart": [{"hooks": [{"command": "x"}, {"command": "y"}]}]}}
        self.assertEqual(len(ci.read_hooks(settings, "global")), 2)

    def test_claude_md_size(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "CLAUDE.md"
            p.write_text("x" * 8000, encoding="utf-8")
            self.assertEqual(ci.approx_tokens(p), 2000)  # bytes // 4


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_config_inspector.py`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
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
            for hook in group.get("hooks", []) or []:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_config_inspector.py`
Expected: `OK` (4 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/config_inspector.py plugins/burn-rate/skills/burn-rate/scripts/test_config_inspector.py
git commit -m "feat: add config inventory inspector"
```

---

## Task 6: attribution.py — Pareto "where to look first"

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/attribution.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_attribution.py`

- [ ] **Step 1: Write the failing test**

```python
# test_attribution.py
import unittest
import attribution
from jsonl_parser import Turn, Usage, Session


def _t(skill=None, plugin=None, agent=None, kind=None, out=100):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s",
                cwd="/tmp/p", timestamp=None, model="claude-opus-4-8",
                usage=Usage(output_tokens=out), session_kind=kind,
                attribution_skill=skill, attribution_plugin=plugin, attribution_agent=agent)


class TestAttribution(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p")
        s.turns = turns
        return s

    def test_groups_by_skill(self):
        s = self._sess([_t(skill="find-skills", out=100), _t(skill="find-skills", out=50),
                        _t(skill="retro", out=30)])
        res = attribution.by_dimension([s], "attribution_skill")
        self.assertEqual(res["find-skills"], 150)
        self.assertEqual(res["retro"], 30)

    def test_workflow_vs_interactive(self):
        s = self._sess([_t(kind="bg", out=200), _t(kind=None, out=100)])
        res = attribution.by_dimension([s], "session_kind")
        self.assertEqual(res["bg"], 200)
        self.assertEqual(res["interactive"], 100)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_attribution.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'attribution'`

- [ ] **Step 3: Write minimal implementation**

```python
# attribution.py
"""Aggregate deduped tokens by attribution dimension -> Pareto 'where to look first'."""
from __future__ import annotations


def by_dimension(sessions: list, attr: str) -> dict:
    """Sum total tokens grouped by a Turn attribute (e.g. 'attribution_skill',
    'attribution_plugin', 'attribution_agent', 'session_kind'). None -> 'interactive'
    for session_kind, else skipped."""
    totals: dict = {}
    for s in sessions:
        for t in s.turns:
            if not t.usage:
                continue
            key = getattr(t, attr, None)
            if key is None:
                if attr == "session_kind":
                    key = "interactive"
                else:
                    continue
            tok = (t.usage.input_tokens + t.usage.output_tokens + t.usage.cache_read_tokens
                   + t.usage.cache_write_5m_tokens + t.usage.cache_write_1h_tokens)
            totals[key] = totals.get(key, 0) + tok
    return totals


def top_n(totals: dict, n: int = 5) -> list:
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:n]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_attribution.py`
Expected: `OK` (2 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/attribution.py plugins/burn-rate/skills/burn-rate/scripts/test_attribution.py
git commit -m "feat: add token attribution Pareto"
```

---

## Task 7: detectors/__init__.py — Leak dataclass + registry

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/detectors/__init__.py`

- [ ] **Step 1: Write the module (no separate test; exercised via detector tests)**

```python
# detectors/__init__.py
"""Leak dataclass + detector registry. Each detector module exposes
`detect(sessions, config, pricing_mod) -> list[Leak]`."""
from __future__ import annotations
from dataclasses import dataclass, field

DETECTOR_MODULES = [
    "detectors.model_selection",
    "detectors.context_rot",
    "detectors.cache",
    "detectors.claude_md_bloat",
]


@dataclass
class Leak:
    id: str
    title: str
    severity: str            # "critical" | "warning" | "suggestion"
    category: str
    evidence: list = field(default_factory=list)
    est_weekly_tokens: int = 0
    est_weekly_cost_usd: float = 0.0
    est_weekly_savings_usd: float = 0.0
    fix_action: str = ""
```

- [ ] **Step 2: Verify import**

Run: `cd plugins/burn-rate/skills/burn-rate/scripts && python3 -c "from detectors import Leak, DETECTOR_MODULES; print(len(DETECTOR_MODULES))"`
Expected: `4`

- [ ] **Step 3: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/__init__.py
git commit -m "feat: add detector registry and Leak type"
```

---

## Task 8: detectors/model_selection.py — combined-signal

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/detectors/model_selection.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_model_selection.py`

Heuristic (improved): count Opus turns that are **interactive** (`not is_sidechain` AND `session_kind != "bg"`) with `output < 1000`. Workflow/subagent inheritance is a *separate* Phase-3 detector, so excluding it here cuts false positives.

- [ ] **Step 1: Write the failing test**

```python
# test_model_selection.py
import unittest
from jsonl_parser import Turn, Usage, Session
import pricing
from detectors import model_selection


def _opus(out, sidechain=False, kind=None):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=None, model="claude-opus-4-8",
                usage=Usage(input_tokens=5, output_tokens=out, cache_read_tokens=1000),
                is_sidechain=sidechain, session_kind=kind)


class TestModelSelection(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p"); s.turns = turns; return s

    def test_flags_interactive_simple_opus(self):
        turns = [_opus(50) for _ in range(40)]
        leaks = model_selection.detect([self._sess(turns)], None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertIn("40", leaks[0].title)

    def test_excludes_sidechain_and_bg(self):
        turns = [_opus(50, sidechain=True) for _ in range(40)] + [_opus(50, kind="bg") for _ in range(40)]
        leaks = model_selection.detect([self._sess(turns)], None, pricing)
        self.assertEqual(leaks, [])

    def test_below_min_count_no_flag(self):
        turns = [_opus(50) for _ in range(5)]
        self.assertEqual(model_selection.detect([self._sess(turns)], None, pricing), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_model_selection.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'detectors.model_selection'`

- [ ] **Step 3: Write minimal implementation**

```python
# detectors/model_selection.py
"""Opus used on interactive simple turns (output < 1k), excluding workflow/subagent
turns (those are a separate fan-out concern). Output length is a weak proxy, so this
is a signal to investigate, not proof."""
from __future__ import annotations
from detectors import Leak

OUTPUT_THRESHOLD = 1000
MIN_TURNS = 30


def detect(sessions, config, pricing) -> list:
    simple = []
    for s in sessions:
        for t in s.turns:
            if not (t.usage and t.model and "opus" in t.model.lower()):
                continue
            if t.is_sidechain or t.session_kind == "bg":
                continue
            if t.usage.output_tokens < OUTPUT_THRESHOLD:
                simple.append(t)
    if len(simple) < MIN_TURNS:
        return []
    opus_cost = sonnet_cost = 0.0
    tokens = 0
    for t in simple:
        b = pricing.TokenBreakdown(
            input_tokens=t.usage.input_tokens, output_tokens=t.usage.output_tokens,
            cache_read_tokens=t.usage.cache_read_tokens,
            cache_write_5m_tokens=t.usage.cache_write_5m_tokens,
            cache_write_1h_tokens=t.usage.cache_write_1h_tokens)
        opus_cost += pricing.estimate_cost(b, t.model)
        sonnet_cost += pricing.estimate_cost(b, "claude-sonnet-4-6")
        tokens += b.total
    savings = round(opus_cost - sonnet_cost, 2)
    severity = "critical" if savings >= 5 else "warning" if savings >= 1 else "suggestion"
    return [Leak(
        id="model_selection:opus_on_interactive_simple",
        title=f"Opus on {len(simple)} interactive simple turns",
        severity=severity, category="model",
        evidence=[f"{len(simple)} interactive Opus turns with <{OUTPUT_THRESHOLD} output tokens",
                  f"Excludes workflow/subagent turns (separate concern)",
                  f"Opus est ${opus_cost:.2f} vs Sonnet est ${sonnet_cost:.2f} (weekly, list)"],
        est_weekly_tokens=tokens, est_weekly_cost_usd=round(opus_cost, 2),
        est_weekly_savings_usd=savings,
        fix_action="Set project default model to Sonnet in .claude/settings.json; escalate to Opus only for hard reasoning.")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_model_selection.py`
Expected: `OK` (3 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/model_selection.py plugins/burn-rate/skills/burn-rate/scripts/test_model_selection.py
git commit -m "feat: add interactive-aware model_selection detector"
```

---

## Task 9: detectors/context_rot.py

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/detectors/context_rot.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_context_rot.py`

- [ ] **Step 1: Write the failing test**

```python
# test_context_rot.py
import unittest
from jsonl_parser import Turn, Usage, Session
import pricing
from detectors import context_rot


def _turn(ctx):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=None, model="claude-opus-4-8",
                usage=Usage(cache_read_tokens=ctx))


class TestContextRot(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p"); s.turns = turns; return s

    def test_flags_when_enough_over_threshold(self):
        turns = [_turn(450_000) for _ in range(12)]
        leaks = context_rot.detect([self._sess(turns)], None, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].category, "context")

    def test_no_flag_below_count(self):
        turns = [_turn(450_000) for _ in range(3)]
        self.assertEqual(context_rot.detect([self._sess(turns)], None, pricing), [])

    def test_no_flag_below_threshold(self):
        turns = [_turn(100_000) for _ in range(20)]
        self.assertEqual(context_rot.detect([self._sess(turns)], None, pricing), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_context_rot.py`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# detectors/context_rot.py
"""Turns past the ~400k context-rot zone (Thariq Shihipar, Anthropic): attention
degrades and re-feeding is expensive. Counts over-threshold turns and excess tokens."""
from __future__ import annotations
from detectors import Leak

ZONE = 400_000
MIN_TURNS = 10


def detect(sessions, config, pricing) -> list:
    over = 0
    excess = 0
    peak = 0
    for s in sessions:
        for t in s.turns:
            if not t.usage:
                continue
            ctx = t.usage.context_size
            peak = max(peak, ctx)
            if ctx > ZONE:
                over += 1
                excess += ctx - ZONE
    if over < MIN_TURNS:
        return []
    return [Leak(
        id="context:rot_zone",
        title=f"{over} turns past the {ZONE // 1000}k context-rot zone",
        severity="warning", category="context",
        evidence=[f"{over} turns over {ZONE // 1000}k context (peak {peak // 1000}k)",
                  f"~{excess:,} excess tokens re-fed past the threshold",
                  "Thariq (Anthropic): the model is least intelligent when compacting late"],
        est_weekly_tokens=excess,
        fix_action="Compact proactively with a scope hint (`/compact focus on X, drop Y`) or start a new session per task.")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_context_rot.py`
Expected: `OK` (3 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/context_rot.py plugins/burn-rate/skills/burn-rate/scripts/test_context_rot.py
git commit -m "feat: add context-rot detector"
```

---

## Task 10: detectors/cache.py — cacheable-minimum aware

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/detectors/cache.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_cache.py`

Improvement over original: only flag low cache-hit when the dominant model's typical prefix is **above** its cacheable minimum — a sub-minimum prefix on Opus can't cache and isn't the user's fault.

- [ ] **Step 1: Write the failing test**

```python
# test_cache.py
import unittest
from jsonl_parser import Turn, Usage, Session
import pricing
from detectors import cache


def _turn(inp, cr):
    return Turn(uuid="u", message_id="m", request_id="r", session_id="s", cwd="/tmp/p",
                timestamp=None, model="claude-opus-4-8",
                usage=Usage(input_tokens=inp, cache_read_tokens=cr))


class TestCache(unittest.TestCase):
    def _sess(self, turns):
        s = Session(session_id="s", cwd="/tmp/p"); s.turns = turns; return s

    def test_flags_low_hit_with_big_input(self):
        # 600k input, only 100k cache read -> hit ratio ~0.14, prefix >> 4096
        turns = [_turn(600_000, 100_000)]
        leaks = cache.detect([self._sess(turns)], None, pricing)
        self.assertEqual(len(leaks), 1)

    def test_no_flag_when_healthy(self):
        turns = [_turn(50_000, 900_000)]  # ~0.95 hit ratio
        self.assertEqual(cache.detect([self._sess(turns)], None, pricing), [])

    def test_no_flag_when_input_tiny(self):
        turns = [_turn(2000, 0)]  # below cacheable minimum, not user's fault
        self.assertEqual(cache.detect([self._sess(turns)], None, pricing), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_cache.py`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# detectors/cache.py
"""Sessions with low cache-hit ratio AND large input — cache churn. Skips sessions
whose input is below the model's cacheable minimum (caching silently can't happen)."""
from __future__ import annotations
from detectors import Leak

MIN_INPUT = 500_000      # only worth flagging above this weekly input
LOW_RATIO = 0.5


def detect(sessions, config, pricing) -> list:
    flagged = []
    for s in sessions:
        u = s.total_usage
        denom = u.input_tokens + u.cache_read_tokens
        if denom < MIN_INPUT:
            continue
        # dominant model cacheable minimum guard
        model = max(s.models_used, key=s.models_used.get) if s.models_used else None
        min_prefix = pricing.cacheable_minimum(model)
        if min_prefix and u.input_tokens < min_prefix * max(1, s.deduped_turn_count):
            continue
        ratio = u.cache_read_tokens / denom if denom else 0.0
        if ratio < LOW_RATIO:
            flagged.append((s, ratio))
    if not flagged:
        return []
    worst = sorted(flagged, key=lambda x: x[1])[:3]
    total_input = sum(s.total_usage.input_tokens for s, _ in flagged)
    return [Leak(
        id="cache:low_hit_ratio",
        title=f"{len(flagged)} sessions with low cache-hit ratio",
        severity="warning", category="cache",
        evidence=[f"{s.project}/{s.session_id[:8]}: hit ratio {r:.0%}, "
                  f"input {s.total_usage.input_tokens:,}" for s, r in worst],
        est_weekly_tokens=total_input,
        fix_action="Avoid mid-session CLAUDE.md edits / project switching that invalidate the cached prefix; keep tools/system stable across the session.")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_cache.py`
Expected: `OK` (3 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/cache.py plugins/burn-rate/skills/burn-rate/scripts/test_cache.py
git commit -m "feat: add cacheable-minimum-aware cache detector"
```

---

## Task 11: detectors/claude_md_bloat.py

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/detectors/claude_md_bloat.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_claude_md_bloat.py`

- [ ] **Step 1: Write the failing test**

```python
# test_claude_md_bloat.py
import unittest
from jsonl_parser import Session
import pricing
from detectors import claude_md_bloat as cmb


class FakeConfig:
    def __init__(self, tokens):
        self.claude_md_tokens = tokens


class TestClaudeMdBloat(unittest.TestCase):
    def test_flags_oversized(self):
        cfg = FakeConfig({"/home/u/.claude/CLAUDE.md": 5000})
        leaks = cmb.detect([Session(session_id="s")], cfg, pricing)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].severity, "warning")

    def test_no_flag_within_target(self):
        cfg = FakeConfig({"/home/u/.claude/CLAUDE.md": 1500})
        self.assertEqual(cmb.detect([Session(session_id="s")], cfg, pricing), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_claude_md_bloat.py`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# detectors/claude_md_bloat.py
"""CLAUDE.md files over the ~2k-token target (paid on every turn). The 2k target is
cited from Anthropic's cost doc but not re-confirmed for 2026 — flagged as such."""
from __future__ import annotations
from detectors import Leak

TARGET = 2000
CRITICAL = 5000


def detect(sessions, config, pricing) -> list:
    if config is None:
        return []
    leaks = []
    for path, tokens in getattr(config, "claude_md_tokens", {}).items():
        if tokens <= TARGET:
            continue
        severity = "critical" if tokens >= CRITICAL else "warning"
        leaks.append(Leak(
            id=f"claude_md:bloat:{path}",
            title=f"CLAUDE.md over target (~{tokens:,} tokens)",
            severity=severity, category="claude_md",
            evidence=[f"{path}: ~{tokens:,} tokens (target ~{TARGET}, cited but not re-confirmed for 2026)",
                      "Paid on every turn of every session",
                      "Non-English structural content tokenizes 2-3x heavier — keep rules in English"],
            est_weekly_tokens=tokens,
            fix_action="Move command recipes/playbooks into separate files loaded on demand via @filename; keep stable rules inline."))
    return leaks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_claude_md_bloat.py`
Expected: `OK` (2 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/claude_md_bloat.py plugins/burn-rate/skills/burn-rate/scripts/test_claude_md_bloat.py
git commit -m "feat: add claude_md bloat detector"
```

---

## Task 12: audit.py — orchestrator

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/audit.py`
- Test: `plugins/burn-rate/skills/burn-rate/scripts/test_audit.py`

- [ ] **Step 1: Write the failing test**

```python
# test_audit.py
import json
import unittest
from unittest import mock
import audit


class TestAudit(unittest.TestCase):
    def test_run_audit_shape(self):
        with mock.patch("audit.jsonl_parser.parse_all", return_value=[]), \
             mock.patch("audit.ccusage.run_daily", return_value=(None, "ccusage skipped")), \
             mock.patch("audit.config_inspector.build_snapshot",
                        return_value=mock.Mock(tool_search_enabled=True, tool_search_mode="default",
                                               hooks=[], mcp_servers=[], plugins=[], skill_count=0,
                                               claude_md_tokens={})):
            result = audit.run_audit(days=7)
        for key in ("summary", "ccusage_error", "bottlenecks", "leaks",
                    "total_weekly_savings_usd", "detector_errors"):
            self.assertIn(key, result)
        # Must be JSON-serializable
        json.dumps(result, default=str)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_audit.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'audit'`

- [ ] **Step 3: Write minimal implementation**

```python
# audit.py
"""burn-rate orchestrator. Local-only token-spend audit -> JSON on stdout.

Runs ccusage for the spend baseline, parses deduped transcripts, inventories config,
computes attribution Pareto, and runs the leak detectors. The SKILL.md body narrates
the JSON in the user's language. Nothing is written; no network except ccusage.
"""
from __future__ import annotations
import argparse
import importlib
import json
from dataclasses import asdict, is_dataclass

import ccusage
import config_inspector
import jsonl_parser
import pricing
import attribution
from detectors import DETECTOR_MODULES


def run_audit(days: int = 7) -> dict:
    ccusage_data, ccusage_error = ccusage.run_daily(days=days)
    sessions = jsonl_parser.parse_all(since_days=days)
    config = config_inspector.build_snapshot()

    leaks, detector_errors = [], []
    for mod_path in DETECTOR_MODULES:
        try:
            mod = importlib.import_module(mod_path)
            leaks.extend(mod.detect(sessions, config, pricing))
        except Exception as e:
            detector_errors.append(f"{mod_path}: {type(e).__name__}: {e}")
    leaks.sort(key=lambda l: l.est_weekly_savings_usd, reverse=True)

    bottlenecks = {
        "by_skill": attribution.top_n(attribution.by_dimension(sessions, "attribution_skill")),
        "by_plugin": attribution.top_n(attribution.by_dimension(sessions, "attribution_plugin")),
        "by_agent": attribution.top_n(attribution.by_dimension(sessions, "attribution_agent")),
        "by_session_kind": attribution.top_n(attribution.by_dimension(sessions, "session_kind")),
    }

    model_mix: dict = {}
    for s in sessions:
        for m, c in s.models_used.items():
            model_mix[m] = model_mix.get(m, 0) + c

    return {
        "summary": {
            "window_days": days,
            "session_count": len(sessions),
            "turn_count": sum(s.deduped_turn_count for s in sessions),
            "model_mix": model_mix,
            "tool_search_enabled": config.tool_search_enabled,
            "tool_search_mode": config.tool_search_mode,
            "hooks": len(config.hooks),
            "skills_installed": config.skill_count,
            "mcp_servers": len(config.mcp_servers),
            "plugins": len(config.plugins),
        },
        "ccusage": ccusage_data,
        "ccusage_error": ccusage_error,
        "detector_errors": detector_errors,
        "bottlenecks": bottlenecks,
        "leaks": [asdict(l) if is_dataclass(l) else l for l in leaks],
        "total_weekly_savings_usd": round(sum(l.est_weekly_savings_usd for l in leaks), 2),
        "pricing_snapshot_date": pricing.SNAPSHOT_DATE,
    }


def main():
    ap = argparse.ArgumentParser(description="Audit Claude Code token usage (read-only).")
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    print(json.dumps(run_audit(days=args.days), indent=2, default=str))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 test_audit.py`
Expected: `OK` (1 test)

- [ ] **Step 5: Run the full test suite**

Run: `cd plugins/burn-rate/skills/burn-rate/scripts && for f in test_*.py detectors/../test_*.py; do python3 "$f"; done`
(Or simply: `python3 -m unittest discover -p 'test_*.py'`)
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/audit.py plugins/burn-rate/skills/burn-rate/scripts/test_audit.py
git commit -m "feat: add burn-rate orchestrator"
```

---

## Task 13: SKILL.md + README.md + reference stubs

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/SKILL.md`
- Create: `plugins/burn-rate/README.md`
- Create: `plugins/burn-rate/skills/burn-rate/references/{leak-taxonomy.md, pricing-2026.md, techniques.md}`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: burn-rate
description: >-
  Audit Claude Code token spend, read-only, and rank where tokens are leaking.
  Deduplicated transcript analysis with skill/plugin/MCP/agent attribution,
  current 2026 pricing, ccusage baseline, and concrete fixes — no config is ever
  modified and nothing is written to disk.

  Use when the user asks to audit token usage, find token leaks, understand why
  they are hitting weekly limits, or optimize Claude Code spend.

  Trigger on: "/burn-rate", "burn rate", "token audit", "where are my tokens
  going", "why am I hitting limits", "optimize my Claude Code", "token leak".

  Skip when: the user wants a luck/retrospective reflection (use lucky-break or
  retro), or wants to APPLY config changes (this skill only diagnoses).
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py *) Read Grep
disallowed-tools: Edit Write
---

# Burn Rate — Read-Only Token-Spend Audit

> Concept and leak taxonomy adapted from *token-audit* by Bayram Annakov —
> https://github.com/BayramAnnakov/token-audit-skill. This is an independent
> implementation.

Find where Claude Code tokens are leaking — and what to fix first. Read-only:
no settings, CLAUDE.md, hooks, or skills are modified, and nothing is written to
disk. All analysis is local; the only network call is the optional `ccusage`
baseline.

## Workflow

### Step 1: Run the audit

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/audit.py" --days 7
```

`${CLAUDE_SKILL_DIR}` resolves to this skill's directory. If — and only if — the
command fails with "No such file or directory" (the variable did not expand),
locate the script with `find ~/.claude -path '*burn-rate*/scripts/audit.py' | head -1`
and run that path. Pass `--days N` to change the window (default 7).

### Step 2: Narrate the JSON as a report

Parse the JSON and write a tight report in the user's conversation language
(default English; for a Russian conversation, write the report in Russian — keep
technical terms like ccusage, /compact, CLAUDE.md, MCP untranslated).

Sections:
1. **Spend summary** — from `ccusage` (total, by model, trend). If `ccusage_error`
   is set, say so and proceed with token counts only.
2. **Where to look first (Pareto)** — from `bottlenecks`: top skills / plugins /
   agents / session-kinds by tokens. This is the attribution view the original
   skill lacks.
3. **Ranked leaks** — for each leak: severity badge (🔴 critical / 🟡 warning /
   🟢 suggestion), evidence bullets with numbers, tokens reclaimable + the fix.
4. **One fix to apply this week** — the single highest-leverage action.

### Step 3: Framing rules (read this)

- **Lead with tokens reclaimed/week and % category reduction**, not dollars.
- Most users are on a flat subscription — put `$` in parentheses labeled
  "reference only at API list pricing — your subscription is flat-fee", and
  translate to **plan headroom** where useful.
- Detector dollars are a **ranking signal**, not billing. The authoritative
  spend figure is the `ccusage` baseline.
- Note honestly: the 2k-token CLAUDE.md target is cited, not re-confirmed for
  2026; the "Opus on simple turns" signal uses output length as a weak proxy.

## What it does NOT do

- Never edits settings.json, CLAUDE.md, hooks, or skills.
- Never writes the report or any file to disk — chat output only.
- No network calls except the optional `ccusage` baseline.
```

- [ ] **Step 2: Write README.md (production-grade)**

```markdown
# burn-rate

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Read-only](https://img.shields.io/badge/mode-read--only-blue.svg)](#)

Read-only audit of Claude Code token spend: deduplicated transcript analysis,
skill/plugin/MCP/agent attribution, current 2026 pricing, a `ccusage` baseline,
and ranked leaks with concrete fixes. **No configuration is ever modified and
nothing is written to disk.**

## Why

`ccusage` and dashboards tell you *how much* you spent; burn-rate tells you
*where it is leaking and what to fix first*. It improves on the original
token-audit concept with deduplicated usage (`message.id` + `requestId`), a
current price model, rich attribution from the transcript, and a diagnostics-only
posture (no confirmation prompts because nothing is changed).

## Install

```
/plugin marketplace add AABur/cc-garden
/plugin install burn-rate@cc-garden
```

## Usage

Run `/burn-rate`, or ask "audit my token usage" / "where are my tokens going".
The skill runs `scripts/audit.py --days 7` and narrates the result in your
language.

Requirements: Python 3.11+. `ccusage` is optional (auto-fetched via `npx`); the
audit still runs without it using token counts only.

## What it checks (Phase 1)

- Opus on interactive simple turns (excludes workflow/subagent fan-out)
- Context-rot zone (>400k-token turns)
- Low cache-hit ratio (cacheable-minimum aware)
- Oversized CLAUDE.md
- Attribution Pareto: tokens by skill / plugin / agent / session-kind

## Privacy

All analysis is local. Only sizes, counts, and names are read — never payloads.
The only network call is the optional `ccusage` baseline.

## Credits

Concept and leak taxonomy adapted from
[token-audit](https://github.com/BayramAnnakov/token-audit-skill) by Bayram
Annakov. The implementation here is original. MIT — see [LICENSE](./LICENSE) for
both copyright lines.
```

- [ ] **Step 3: Write reference stubs**

`references/pricing-2026.md`:
```markdown
# Pricing snapshot — 2026-06-04

USD per million tokens. Source: Anthropic `claude-api` skill (cached 2026-06-04).
ccusage remains the authority for the spend baseline; this table powers per-leak
detector estimates only.

| family | input | output | cache_write_5m | cache_write_1h | cache_read | cacheable_min |
|---|---|---|---|---|---|---|
| opus (4.x) | 5 | 25 | 6.25 | 10 | 0.5 | 4096 |
| sonnet (4.6) | 3 | 15 | 3.75 | 6 | 0.3 | 2048 |
| haiku (4.5) | 1 | 5 | 1.25 | 2 | 0.1 | 4096 |
| fable-5 | 10 | 50 | 12.5 | 20 | 1.0 | 2048 |

Current 1M-context models carry no long-context premium. Refresh this table when
Anthropic pricing changes; the spend baseline stays current automatically via
ccusage's online price refresh.
```

`references/leak-taxonomy.md`:
```markdown
# Leak taxonomy (Phase 1)

| id | what it catches | source |
|---|---|---|
| model_selection:opus_on_interactive_simple | Opus on short interactive turns (excl. fan-out) | adapted from token-audit |
| context:rot_zone | turns past ~400k context | Thariq Shihipar, Anthropic |
| cache:low_hit_ratio | cache churn, cacheable-minimum aware | adapted from token-audit |
| claude_md:bloat | CLAUDE.md over ~2k tokens | Anthropic cost doc (cited) |

Phase 2 adds: hook_bloat, skill_descriptions, bash_antipatterns, file_reads,
recurring_scripts, tool_schema. Phase 3 adds: subagent_fanout, effort_audit,
error_retries, cache_invalidators.
```

`references/techniques.md`:
```markdown
# Token-engineering levers (2026)

Prompt caching (5m=1.25x / 1h=2x write, read ~0.1x; per-model cacheable minimum),
context editing / proactive `/compact` (context rot past ~400k), per-subagent
model selection, tool-search vs full MCP schema loading, `effort` parameter
(Sonnet 4.6 defaults to high), subagent fan-out multiplier, `.claudeignore`,
plan-mode, `@file` vs pasted blobs. See spec for sourcing.
```

- [ ] **Step 4: Validate SKILL.md frontmatter parses**

Run: `python3 -c "import re,sys; t=open('plugins/burn-rate/skills/burn-rate/SKILL.md').read(); assert t.startswith('---'); print('frontmatter OK')"`
Expected: `frontmatter OK`

- [ ] **Step 5: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/SKILL.md plugins/burn-rate/README.md plugins/burn-rate/skills/burn-rate/references/
git commit -m "docs: add burn-rate SKILL.md, README, and references"
```

---

## Task 14: End-to-end verification & comparison

**Files:** none (verification only)

- [ ] **Step 1: Run the real audit**

Run: `python3 plugins/burn-rate/skills/burn-rate/scripts/audit.py --days 7 > /tmp/burn-rate-out.json; python3 -c "import json; d=json.load(open('/tmp/burn-rate-out.json')); print('detector_errors:', d['detector_errors']); print('sessions:', d['summary']['session_count']); print('leaks:', len(d['leaks']))"`
Expected: `detector_errors: []`, non-zero sessions, some leaks.

- [ ] **Step 2: Confirm no overcount vs ccusage**

Compare the deduped Opus token total in the output to `ccusage daily --json` for the same window. The burn-rate Opus token total must be **≤** ccusage's (dedup must not inflate). Note the result in the PR description.

- [ ] **Step 3: Full test suite green**

Run: `cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m unittest discover -p 'test_*.py' -v`
Expected: all tests pass, 0 failures/errors.

- [ ] **Step 4: A/B against token-audit (manual)**

Run both audits on the same machine/window: `/burn-rate` and `/token-audit`. Diff the reports. Confirm burn-rate's numbers reconcile with ccusage where the original's did not (the $672 vs $171 class of error should be gone). Record findings for the PR.

- [ ] **Step 5: Open PR**

```bash
git push -u origin feat/burn-rate
gh pr create --title "feat: add burn-rate token-audit skill (Phase 1 MVP)" --body "Phase 1 of burn-rate per docs/superpowers/specs/2026-06-11-burn-rate-design.md. Read-only token-spend audit: deduped parser, 2026 pricing, attribution Pareto, 4 detectors. Credits: concept/taxonomy from BayramAnnakov/token-audit-skill."
```

---

## Self-Review

**Spec coverage:** §3 architecture → Tasks 2-13 (all modules). §4 Phase 1 detectors → Tasks 8-11. §5 pricing → Task 2. §6 report → Task 13 SKILL.md. §7 privacy/read-only → SKILL.md frontmatter (disallowed Edit/Write) + parser comments. §8 packaging/credits → Tasks 1, 13. §9 testing → every task TDD. §10 verification → Task 14. Dedup (§1 fix) → Task 3. Attribution (§1 advantage) → Tasks 3, 6. Covered.

**Placeholder scan:** No TBD/TODO; every code step has complete code; commands have expected output.

**Type consistency:** `TokenBreakdown` fields (`cache_write_5m_tokens` etc.) consistent across pricing.py, model_selection.py, audit.py. `Usage` fields (`cache_write_5m_tokens`, `context_size`) consistent across parser, detectors, attribution. `Leak` fields consistent across `__init__.py`, detectors, audit. Detector signature `detect(sessions, config, pricing)` uniform across Tasks 8-12.

**Out of Phase 1 scope (later phases):** Phase 2 parity detectors and Phase 3 new detectors (`subagent_fanout`, `effort_audit`, `error_retries`, `cache_invalidators`) get their own plans.
