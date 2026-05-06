# retro

Conversational archaeology for a Claude Code project. The `/retro` skill
reconstructs the *decision history* of the current repository from local
session JSONLs — the part that lives in chats, not in git.

## What it does

Runs a single-shot workflow:

1. Resolves the project root via `git rev-parse --show-toplevel`. Fails
   cleanly outside a git repo.
2. Discovers all session JSONLs that belong to this project, including
   subdirectory-launched sessions, Claude worktrees, and subagent threads.
3. Extracts a bounded evidence pack via a deterministic stdlib-only Python
   parser (`scripts/extract_sessions.py`):
   - Streams JSONL line-by-line.
   - Walks nested `message.content[]` correctly (no flat-parse confusion
     between `tool_use` and assistant text).
   - Skips `thinking` blocks (counts only) and never emits `signature`
     fields.
   - Redacts API keys, GitHub PATs, AWS keys, JWTs, `Authorization:`
     headers.
   - Caps total evidence at a configurable character budget; subagents
     get a separate 25% sub-budget to keep the main thread primary.
4. Hands the pack to the model, which writes a Markdown retrospective
   following `references/report-prompt.md`:
   - **A.** Decision timeline.
   - **B.** Abandoned approaches & loops.
   - **C.** Topic & focus map.
   - **D.** Initial intent vs later stated state.
   - **F.** Recommended CLAUDE.md rules tied to concrete failure patterns.
5. Writes the report to `.retro/retrospectives/<YYYY-MM-DD>-retro.md`
   (gitignored by default).

## Install

```
/plugin install retro@cc-garden
```

## Usage

From the root of any git repository:

```
/retro
```

The skill produces `.retro/retrospectives/<today>-retro.md`. Inspect it,
edit it, share it — it is yours.

## Output structure

After the first run, the project gains:

```
.retro/
├── .gitignore               # contains retrospectives/ and .tmp/
├── config.json              # committable; tiny, no private data
├── retrospectives/          # gitignored
│   └── <YYYY-MM-DD>-retro.md
└── .tmp/                    # gitignored, removed after each run by default
```

`config.json` schema:

| Key | Default | Meaning |
|-----|---------|---------|
| `version` | `1` | Config schema version. |
| `language` | `null` | `null` = autodetect each run. Set to `"en"` or `"ru"` to lock. |
| `include_repo_metadata` | `true` | Allow injecting README / git log as `external` evidence. |
| `evidence_budget_chars` | `320000` | Hard cap on the evidence pack (~80K tokens). |
| `keep_tmp` | `false` | If `true`, retain `.retro/.tmp/` after each run for debug. |

## Design notes

- **Extractor-first.** The riskiest part is JSONL parsing, not the skill
  text. The Python parser is deterministic, stdlib-only, and unit-tested
  (`scripts/test_extract_sessions.py`).
- **Bounded evidence.** A character budget is enforced before the model
  ever sees the pack. The model receives a curated digest, not raw logs.
- **Citations on findings.** Every entry in sections A, B, and F must
  carry a citation anchor. Generic rules without a tied failure pattern
  are forbidden.
- **Privacy by default.** Reports are gitignored. Pasted blocks larger
  than 4 KB are dropped. Common secret patterns are redacted in the
  evidence pack.
- **Sidechain capped at 25%.** Subagent transcripts are tagged and their
  share of the evidence budget is hard-capped, so they cannot drown the
  main user-assistant decision narrative.

## Run the parser tests

```
python3 plugins/retro/scripts/test_extract_sessions.py
```

23 unit tests covering parser shapes, redaction, classifier, budget
allocation, language detection, and session discovery.

## Limitations

- MVP: no chunking, no continuous retro, no cross-project view.
- Language autodetection samples only recent main-thread user prompts; if
  the result feels wrong, set `language` in `config.json`.
- Worktree directory pattern recognised: `<flat-root>--claude-worktrees-*`.
- Tested on macOS with default Python 3 (3.9+); should work anywhere
  stdlib `subprocess`, `pathlib`, `re`, `json` are available.
