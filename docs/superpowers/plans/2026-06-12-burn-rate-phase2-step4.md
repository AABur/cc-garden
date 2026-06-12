# Burn-Rate Phase 2 Step 4: Leak Metadata + Causal Detectors

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three metadata fields to the `Leak` dataclass, update all existing detector signatures to accept `causal_events`, and implement three new causal detectors (`hook_output_bloat`, `bash_antipatterns`, `repeated_reads`) with full test coverage.

**Architecture:** All detectors share a uniform `detect(sessions, causal_events, config, pricing)` signature. Existing detectors accept but ignore `causal_events` (they are spend-basis). The three new detectors are causal-basis and operate on `CausalEvent` objects from `jsonl_parser`. The `Leak` dataclass gets three metadata fields with defaults so old detectors need no argument changes.

**Tech Stack:** Python 3.14, pytest, stdlib only (dataclasses, collections.Counter)

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `detectors/__init__.py` | Add `basis`, `additive`, `overlap_group` to `Leak`; add new module paths to `DETECTOR_MODULES` |
| Modify | `detectors/model_selection.py` | Add `causal_events` param (ignored) |
| Modify | `detectors/context_rot.py` | Add `causal_events` param (ignored) |
| Modify | `detectors/cache.py` | Add `causal_events` param (ignored) |
| Modify | `detectors/claude_md_bloat.py` | Add `causal_events` param (ignored) |
| Modify | `audit.py` | Pass `_causal_events` to `mod.detect(...)` |
| Create | `detectors/hook_output_bloat.py` | Causal detector: flag large hook output per session |
| Create | `detectors/bash_antipatterns.py` | Causal detector: flag shell read/search tools |
| Create | `detectors/repeated_reads.py` | Causal detector: flag files read > 3x per session |
| Create | `test_hook_output_bloat.py` | Tests for hook_output_bloat |
| Create | `test_bash_antipatterns.py` | Tests for bash_antipatterns |
| Create | `test_repeated_reads.py` | Tests for repeated_reads |

All files live under: `plugins/burn-rate/skills/burn-rate/scripts/`

Run tests with:
```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest . -v
```

---

### Task 1: Add metadata fields to `Leak` dataclass

**Files:**
- Modify: `plugins/burn-rate/skills/burn-rate/scripts/detectors/__init__.py`

- [ ] **Step 1: Read the current `__init__.py` to understand the exact structure**

The file currently contains:
```python
@dataclass
class Leak:
    id: str
    title: str
    severity: str
    category: str
    evidence: list = field(default_factory=list)
    est_weekly_tokens: int = 0
    est_weekly_cost_usd: float = 0.0
    est_weekly_savings_usd: float = 0.0
    fix_action: str = ""
```

- [ ] **Step 2: Add three metadata fields with defaults after `category`**

Edit `detectors/__init__.py`. Replace the `Leak` dataclass body with:

```python
@dataclass
class Leak:
    id: str
    title: str
    severity: str
    category: str
    basis: str = "spend"       # "spend", "causal", "workload", "mixed"
    additive: bool = False
    overlap_group: str = ""
    evidence: list = field(default_factory=list)
    est_weekly_tokens: int = 0
    est_weekly_cost_usd: float = 0.0
    est_weekly_savings_usd: float = 0.0
    fix_action: str = ""

    def __post_init__(self):
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}, got {self.severity!r}")
```

Note: `basis`, `additive`, `overlap_group` have defaults so all existing detectors still work without changes.

- [ ] **Step 3: Verify all 70 existing tests still pass**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest . -v --tb=short
```

Expected: 70 passed, 0 failed.

- [ ] **Step 4: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/__init__.py
git commit -m "feat: add basis/additive/overlap_group metadata to Leak dataclass"
```

---

### Task 2: Update existing detector signatures

**Files:**
- Modify: `plugins/burn-rate/skills/burn-rate/scripts/detectors/model_selection.py`
- Modify: `plugins/burn-rate/skills/burn-rate/scripts/detectors/context_rot.py`
- Modify: `plugins/burn-rate/skills/burn-rate/scripts/detectors/cache.py`
- Modify: `plugins/burn-rate/skills/burn-rate/scripts/detectors/claude_md_bloat.py`
- Modify: `plugins/burn-rate/skills/burn-rate/scripts/audit.py`

- [ ] **Step 1: Update `model_selection.py` signature**

Change line:
```python
def detect(sessions, config, pricing) -> list:
```
To:
```python
def detect(sessions, causal_events, config, pricing) -> list:
```

- [ ] **Step 2: Update `context_rot.py` signature**

Change line:
```python
def detect(sessions, config, pricing) -> list:
```
To:
```python
def detect(sessions, causal_events, config, pricing) -> list:
```

- [ ] **Step 3: Update `cache.py` signature**

Change line:
```python
def detect(sessions, config, pricing) -> list:
```
To:
```python
def detect(sessions, causal_events, config, pricing) -> list:
```

- [ ] **Step 4: Update `claude_md_bloat.py` signature**

Change line:
```python
def detect(sessions, config, pricing) -> list:
```
To:
```python
def detect(sessions, causal_events, config, pricing) -> list:
```

- [ ] **Step 5: Update `audit.py` to pass `_causal_events`**

In `audit.py`, change line (around line 34):
```python
leaks.extend(mod.detect(sessions, config, pricing))
```
To:
```python
leaks.extend(mod.detect(sessions, _causal_events, config, pricing))
```

- [ ] **Step 6: Verify all 70 tests still pass**

The existing tests call detectors with `(sessions, None, pricing)` — this now maps to `(sessions, causal_events=None, config=None, pricing)` which breaks the positional order.

Check the existing test files to understand the call pattern. In `test_cache.py`:
```python
leaks = cache.detect([self._sess(turns)], None, pricing)
```

After the signature change to `detect(sessions, causal_events, config, pricing)`, this call `(sessions, None, pricing)` passes `None` for `causal_events` and `pricing` for `config`, which is wrong.

**The existing tests must be updated too.** Each test that calls `detector.detect(sessions, None, pricing)` must become `detector.detect(sessions, [], None, pricing)`.

Update `test_cache.py`: change all `cache.detect([...], None, pricing)` to `cache.detect([...], [], None, pricing)`.

Update `test_context_rot.py`: change all `context_rot.detect([...], None, pricing)` to `context_rot.detect([...], [], None, pricing)`.

Update `test_model_selection.py`: change all `model_selection.detect([...], None, pricing)` to `model_selection.detect([...], [], None, pricing)`.

Update `test_claude_md_bloat.py`: change all `claude_md_bloat.detect([...], ...)` to pass `[]` as second argument.

Run tests to confirm:
```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest . -v --tb=short
```

Expected: 70 passed, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/model_selection.py \
        plugins/burn-rate/skills/burn-rate/scripts/detectors/context_rot.py \
        plugins/burn-rate/skills/burn-rate/scripts/detectors/cache.py \
        plugins/burn-rate/skills/burn-rate/scripts/detectors/claude_md_bloat.py \
        plugins/burn-rate/skills/burn-rate/scripts/audit.py \
        plugins/burn-rate/skills/burn-rate/scripts/test_cache.py \
        plugins/burn-rate/skills/burn-rate/scripts/test_context_rot.py \
        plugins/burn-rate/skills/burn-rate/scripts/test_model_selection.py \
        plugins/burn-rate/skills/burn-rate/scripts/test_claude_md_bloat.py
git commit -m "feat: add causal_events param to all detector signatures"
```

---

### Task 3: Failing tests for `hook_output_bloat`

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/test_hook_output_bloat.py`

- [ ] **Step 1: Write the failing tests**

Create `test_hook_output_bloat.py`:

```python
# test_hook_output_bloat.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import CausalEvent  # noqa: E402


def _ev(session_id, content_size, event_type="tool_result", tool_name="Bash"):
    return CausalEvent(
        tool_use_id="tid",
        session_id=session_id,
        event_type=event_type,
        tool_name=tool_name,
        content_size=content_size,
    )


class TestHookOutputBloat(unittest.TestCase):

    def test_flags_when_avg_content_size_exceeds_threshold_and_enough_sessions(self):
        # 3 sessions, each with a single tool_result of 60_000 chars -> avg 60k > 50k
        events = [
            _ev("s1", 60_000),
            _ev("s2", 60_000),
            _ev("s3", 60_000),
        ]
        from detectors import hook_output_bloat
        leaks = hook_output_bloat.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "causal:hook_output_bloat")
        self.assertEqual(leaks[0].severity, "warning")
        self.assertEqual(leaks[0].basis, "causal")
        self.assertEqual(leaks[0].overlap_group, "hook_bloat")

    def test_no_flag_when_content_size_small(self):
        # 3 sessions, each with 1_000 chars -> avg 1k < 50k
        events = [
            _ev("s1", 1_000),
            _ev("s2", 1_000),
            _ev("s3", 1_000),
        ]
        from detectors import hook_output_bloat
        leaks = hook_output_bloat.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_no_flag_when_fewer_than_3_sessions(self):
        # 2 sessions with large content_size -> not enough sessions
        events = [
            _ev("s1", 100_000),
            _ev("s2", 100_000),
        ]
        from detectors import hook_output_bloat
        leaks = hook_output_bloat.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_no_flag_when_no_causal_events(self):
        from detectors import hook_output_bloat
        leaks = hook_output_bloat.detect([], [], None, None)
        self.assertEqual(leaks, [])

    def test_only_tool_result_events_counted(self):
        # Mix of event types — only tool_result should count
        events = [
            _ev("s1", 60_000, event_type="tool_result"),
            _ev("s2", 60_000, event_type="tool_result"),
            _ev("s3", 60_000, event_type="tool_result"),
            CausalEvent(tool_use_id="x", session_id="s4", event_type="other",
                        tool_name="Bash", content_size=999_999),
        ]
        from detectors import hook_output_bloat
        leaks = hook_output_bloat.detect([], events, None, None)
        # s4 has no tool_result events -> only 3 sessions qualify -> should flag
        self.assertEqual(len(leaks), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest test_hook_output_bloat.py -v --tb=short
```

Expected: ImportError or ModuleNotFoundError for `detectors.hook_output_bloat`.

- [ ] **Step 3: Commit failing tests**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/test_hook_output_bloat.py
git commit -m "test: add failing tests for hook_output_bloat detector"
```

---

### Task 4: Implement `hook_output_bloat` detector

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/detectors/hook_output_bloat.py`

- [ ] **Step 1: Create the implementation**

Create `detectors/hook_output_bloat.py`:

```python
# detectors/hook_output_bloat.py
"""Detects sessions where hook output creates measurable context tax."""
from . import Leak

BLOAT_THRESHOLD_CHARS = 50_000    # aggregate tool_result content per session
MIN_SESSIONS = 3                   # noise filter


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    # Sum content_size for tool_result events, grouped by session_id.
    by_session: dict[str, int] = {}
    for ev in causal_events:
        if ev.event_type != "tool_result":
            continue
        by_session[ev.session_id] = by_session.get(ev.session_id, 0) + ev.content_size

    if len(by_session) < MIN_SESSIONS:
        return []

    total = sum(by_session.values())
    avg = total / len(by_session)

    if avg <= BLOAT_THRESHOLD_CHARS:
        return []

    # Top 3 sessions by content size for evidence.
    top3 = sorted(by_session.items(), key=lambda x: x[1], reverse=True)[:3]
    est_tokens = total // 4  # approximate chars-to-tokens ratio

    return [Leak(
        id="causal:hook_output_bloat",
        title="Large tool output injected into context",
        severity="warning",
        category="workflow",
        basis="causal",
        overlap_group="hook_bloat",
        additive=False,
        evidence=[
            f"{len(by_session)} sessions with tool_result events",
            f"Average tool output per session: {avg:,.0f} chars",
        ] + [f"  {sid[:8]}: {size:,} chars" for sid, size in top3],
        est_weekly_tokens=est_tokens,
        est_weekly_cost_usd=0.0,
        est_weekly_savings_usd=0.0,
        fix_action="Review hook output size; large hook outputs are injected into context on every turn",
    )]
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest test_hook_output_bloat.py -v --tb=short
```

Expected: 5 passed, 0 failed.

- [ ] **Step 3: Run full suite to confirm no regressions**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest . -v --tb=short
```

Expected: 75 passed, 0 failed.

- [ ] **Step 4: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/hook_output_bloat.py
git commit -m "feat: add hook_output_bloat causal detector"
```

---

### Task 5: Failing tests for `bash_antipatterns`

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/test_bash_antipatterns.py`

- [ ] **Step 1: Write the failing tests**

Create `test_bash_antipatterns.py`:

```python
# test_bash_antipatterns.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import CausalEvent  # noqa: E402


def _bash_ev(session_id, command_head):
    return CausalEvent(
        tool_use_id="tid",
        session_id=session_id,
        event_type="tool_result",
        tool_name="Bash",
        command_head=command_head,
        content_size=100,
    )


class TestBashAntipatterns(unittest.TestCase):

    def _make_events(self, cmd, count):
        return [_bash_ev(f"s{i}", cmd) for i in range(count)]

    def test_detects_cat_head_tail_commands(self):
        # 12 cat calls -> above MIN_COUNT=10
        events = self._make_events("cat /some/file.py", 12)
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "causal:bash_antipatterns")
        self.assertEqual(leaks[0].severity, "suggestion")
        self.assertEqual(leaks[0].basis, "causal")
        self.assertIn("12", leaks[0].evidence[0])

    def test_detects_mixed_shell_readers(self):
        # 4 cat + 4 grep + 4 head = 12 total
        events = (
            self._make_events("cat file.txt", 4) +
            self._make_events("grep pattern file.txt", 4) +
            self._make_events("head -n 20 file.txt", 4)
        )
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)

    def test_no_flag_when_below_min_count(self):
        # Only 5 cat calls -> below MIN_COUNT=10
        events = self._make_events("cat /some/file.py", 5)
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_non_bash_tools_not_counted(self):
        # 12 Read tool events -> tool_name is "Read", not "Bash"
        events = [
            CausalEvent(
                tool_use_id="tid",
                session_id=f"s{i}",
                event_type="tool_result",
                tool_name="Read",
                command_head="cat /file",   # command_head has cat but tool is Read
                content_size=100,
            )
            for i in range(12)
        ]
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_non_shell_bash_commands_not_counted(self):
        # 12 Bash calls with non-shell-reader command
        events = self._make_events("git status", 12)
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_empty_command_head_skipped(self):
        events = [
            CausalEvent(
                tool_use_id="tid",
                session_id=f"s{i}",
                event_type="tool_result",
                tool_name="Bash",
                command_head="",
                content_size=100,
            )
            for i in range(20)
        ]
        from detectors import bash_antipatterns
        leaks = bash_antipatterns.detect([], events, None, None)
        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest test_bash_antipatterns.py -v --tb=short
```

Expected: ImportError or ModuleNotFoundError for `detectors.bash_antipatterns`.

- [ ] **Step 3: Commit failing tests**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/test_bash_antipatterns.py
git commit -m "test: add failing tests for bash_antipatterns detector"
```

---

### Task 6: Implement `bash_antipatterns` detector

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/detectors/bash_antipatterns.py`

- [ ] **Step 1: Create the implementation**

Create `detectors/bash_antipatterns.py`:

```python
# detectors/bash_antipatterns.py
"""Flags shell reads/searches where native Claude Code tools would be cheaper."""
from . import Leak

SHELL_READERS = {"cat", "head", "tail", "sed", "awk", "grep", "find"}
MIN_COUNT = 10   # noise filter


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    matches = []
    for ev in causal_events:
        if ev.tool_name != "Bash" or not ev.command_head:
            continue
        first_word = ev.command_head.strip().split()[0] if ev.command_head.strip() else ""
        if first_word in SHELL_READERS:
            matches.append(ev)
    if len(matches) < MIN_COUNT:
        return []
    return [Leak(
        id="causal:bash_antipatterns",
        title="Shell reads/searches in Claude Code",
        severity="suggestion",
        category="workflow",
        basis="causal",
        overlap_group="bash_patterns",
        additive=False,
        evidence=[
            f"{len(matches)} shell read/search calls detected (cat/head/tail/sed/awk/grep/find)",
            "In Claude Code, native Read/Grep tools are cheaper and bypass the shell overhead",
            "Some calls may be intentional (e.g. piped commands, complex transformations)",
        ],
        est_weekly_tokens=0,
        est_weekly_cost_usd=0.0,
        est_weekly_savings_usd=0.0,
        fix_action="Prefer Read, Grep, and other native Claude Code tools over shell equivalents when possible",
    )]
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest test_bash_antipatterns.py -v --tb=short
```

Expected: 6 passed, 0 failed.

- [ ] **Step 3: Run full suite to confirm no regressions**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest . -v --tb=short
```

Expected: 81 passed, 0 failed.

- [ ] **Step 4: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/bash_antipatterns.py
git commit -m "feat: add bash_antipatterns causal detector"
```

---

### Task 7: Failing tests for `repeated_reads`

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/test_repeated_reads.py`

- [ ] **Step 1: Write the failing tests**

Create `test_repeated_reads.py`:

```python
# test_repeated_reads.py
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jsonl_parser import CausalEvent  # noqa: E402


def _read_ev(session_id, file_path, content_size, tool_name="Read"):
    return CausalEvent(
        tool_use_id="tid",
        session_id=session_id,
        event_type="tool_result",
        tool_name=tool_name,
        file_path=file_path,
        content_size=content_size,
    )


class TestRepeatedReads(unittest.TestCase):

    def test_flags_file_read_more_than_3_times_with_large_content(self):
        # Same file read 4 times in same session, each 3_000 chars -> total 12k >= 10k
        events = [_read_ev("s1", "/project/big_file.py", 3_000) for _ in range(4)]
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0].id, "causal:repeated_reads")
        self.assertEqual(leaks[0].severity, "suggestion")
        self.assertEqual(leaks[0].basis, "causal")
        self.assertIn("/project/big_file.py", leaks[0].evidence[0])
        self.assertIn("4", leaks[0].evidence[0])

    def test_no_flag_when_read_count_at_threshold(self):
        # Exactly 3 reads -> not OVER threshold (threshold is > 3)
        events = [_read_ev("s1", "/project/file.py", 5_000) for _ in range(3)]
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_no_flag_when_content_size_small(self):
        # File read 5 times but total content_size = 5 * 1_000 = 5_000 < 10_000
        events = [_read_ev("s1", "/project/tiny.py", 1_000) for _ in range(5)]
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_reads_in_different_sessions_not_combined(self):
        # Same file read 2 times each in 3 different sessions -> per-session count is 2 (not over threshold)
        events = (
            [_read_ev("s1", "/project/file.py", 5_000)] * 2 +
            [_read_ev("s2", "/project/file.py", 5_000)] * 2 +
            [_read_ev("s3", "/project/file.py", 5_000)] * 2
        )
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(leaks, [])

    def test_edit_and_write_tools_also_counted(self):
        # 2 Read + 2 Edit in same session for same file = 4 total -> flag
        events = (
            [_read_ev("s1", "/project/file.py", 3_000, tool_name="Read")] * 2 +
            [_read_ev("s1", "/project/file.py", 3_000, tool_name="Edit")] * 2
        )
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(len(leaks), 1)

    def test_no_flag_when_file_path_empty(self):
        # Events with empty file_path should be ignored
        events = [
            CausalEvent(
                tool_use_id="tid",
                session_id="s1",
                event_type="tool_result",
                tool_name="Read",
                file_path="",
                content_size=5_000,
            )
            for _ in range(5)
        ]
        from detectors import repeated_reads
        leaks = repeated_reads.detect([], events, None, None)
        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest test_repeated_reads.py -v --tb=short
```

Expected: ImportError or ModuleNotFoundError for `detectors.repeated_reads`.

- [ ] **Step 3: Commit failing tests**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/test_repeated_reads.py
git commit -m "test: add failing tests for repeated_reads detector"
```

---

### Task 8: Implement `repeated_reads` detector

**Files:**
- Create: `plugins/burn-rate/skills/burn-rate/scripts/detectors/repeated_reads.py`

- [ ] **Step 1: Create the implementation**

Create `detectors/repeated_reads.py`:

```python
# detectors/repeated_reads.py
"""Flags files read more than 3 times in a single session (low-confidence hint)."""
from collections import Counter
from . import Leak

READ_THRESHOLD = 3
MIN_CONTENT_SIZE = 10_000  # suppress if small files


def detect(sessions, causal_events, config, pricing) -> list[Leak]:
    by_session: dict[str, list] = {}
    for ev in causal_events:
        if ev.tool_name not in {"Read", "Edit", "Write"} or not ev.file_path:
            continue
        by_session.setdefault(ev.session_id, []).append(ev)

    repeated = []
    for sess_id, events in by_session.items():
        counts = Counter(ev.file_path for ev in events)
        for path, count in counts.items():
            if count <= READ_THRESHOLD:
                continue
            total_size = sum(ev.content_size for ev in events if ev.file_path == path)
            if total_size >= MIN_CONTENT_SIZE:
                repeated.append((path, count, sess_id))

    if not repeated:
        return []

    evidence = [
        f"{path} accessed {count} times in session {sid[:8]}"
        for path, count, sid in repeated[:3]
    ]
    return [Leak(
        id="causal:repeated_reads",
        title="Repeated file reads in sessions",
        severity="suggestion",
        category="workflow",
        basis="causal",
        overlap_group="repeated_reads",
        additive=False,
        evidence=evidence + ["Consider caching file content in a variable or using /compact"],
        est_weekly_tokens=0,
        est_weekly_cost_usd=0.0,
        est_weekly_savings_usd=0.0,
        fix_action="Cache frequently-read file content within a session; use /compact to trim context",
    )]
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest test_repeated_reads.py -v --tb=short
```

Expected: 6 passed, 0 failed.

- [ ] **Step 3: Run full suite to confirm no regressions**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest . -v --tb=short
```

Expected: 87 passed, 0 failed.

- [ ] **Step 4: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/repeated_reads.py
git commit -m "feat: add repeated_reads causal detector"
```

---

### Task 9: Register new detectors in `audit.py`

**Files:**
- Modify: `plugins/burn-rate/skills/burn-rate/scripts/detectors/__init__.py`

- [ ] **Step 1: Add new module paths to `DETECTOR_MODULES`**

In `detectors/__init__.py`, change:
```python
DETECTOR_MODULES = [
    "detectors.model_selection",
    "detectors.context_rot",
    "detectors.cache",
    "detectors.claude_md_bloat",
]
```
To:
```python
DETECTOR_MODULES = [
    "detectors.model_selection",
    "detectors.context_rot",
    "detectors.cache",
    "detectors.claude_md_bloat",
    "detectors.hook_output_bloat",
    "detectors.bash_antipatterns",
    "detectors.repeated_reads",
]
```

- [ ] **Step 2: Run full test suite**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 -m pytest . -v --tb=short
```

Expected: 87 passed, 0 failed.

- [ ] **Step 3: Spot-check audit integration (optional smoke test)**

```bash
cd plugins/burn-rate/skills/burn-rate/scripts && python3 audit.py --skip-ccusage --days 1 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print('detector_errors:', d['detector_errors']); print('leak_ids:', [l['id'] for l in d['leaks']])"
```

Expected: `detector_errors: []` (no import or runtime failures from the new detectors).

- [ ] **Step 4: Commit**

```bash
git add plugins/burn-rate/skills/burn-rate/scripts/detectors/__init__.py
git commit -m "feat: register hook_output_bloat, bash_antipatterns, repeated_reads in DETECTOR_MODULES"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `Leak` fields `basis`, `additive`, `overlap_group` added with defaults (Task 1)
- [x] All 4 existing detectors get `causal_events` second positional arg (Task 2)
- [x] `audit.py` passes `_causal_events` to `mod.detect(...)` (Task 2)
- [x] `hook_output_bloat` detector created with correct logic and `basis="causal"` (Tasks 3-4)
- [x] `bash_antipatterns` detector created (Tasks 5-6)
- [x] `repeated_reads` detector created (Tasks 7-8)
- [x] All three registered in `DETECTOR_MODULES` (Task 9)
- [x] 3+ tests per new detector (Tasks 3, 5, 7: 5, 6, 6 tests respectively)
- [x] Existing 70 tests must stay green — accounted for in Task 2 Step 6

**Key risk noted:** Existing tests call detectors with `(sessions, None, pricing)`. After the signature change they pass wrong values positionally. Task 2 Step 6 explicitly updates all affected test files.

**Type consistency:**
- `CausalEvent` imported from `jsonl_parser` consistently across all test files
- `Leak` fields `basis`, `additive`, `overlap_group` used consistently in all three new detectors
- `causal_events` parameter name consistent across all 7 detector files
