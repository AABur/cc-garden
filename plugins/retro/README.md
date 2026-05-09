# retro

Generate a **human-readable project retrospective** from your Claude Code
session history. The `/retro` skill reads the conversation logs Claude
Code keeps for the current repository and writes a synthesis-first
Markdown report you can read in five minutes — what happened, what
worked, what did not, what is unresolved, what to do next — backed by a
detailed evidence appendix with citations.

## Install

```
/plugin marketplace add AABur/cc-garden
/plugin install retro@cc-garden
```

## Usage

From the root of any git repository:

```
/retro
```

The skill writes the report to `<repo>/.retro/<YYYY-MM-DD>-retro.md`.
On the first run in a repo it asks which language to use; subsequent
runs read the language from the most recent report's header tag
(`<!-- retro-language: <code> -->`) and skip the question.

## What the report looks like

```
# Retrospective: <project-name>
<!-- retro-language: en -->

(header: generation date, project root, sessions analyzed, date range,
 evidence policy, privacy notice)

## TL;DR
3-5 sentences. The main project conclusion plus the most important
next decision the project owner faces.

## What Happened
2-4 phases. Synthesis, not an event list.

## What Worked
2-5 specific bullets. Practices, decisions, or workflows that helped.

## What Did Not Work
2-5 specific bullets. Failure patterns, stalls, repeated loops,
avoidable friction. No blame.

## Open Loops
Each unresolved thread with: topic, current state, blocker,
recommended decision.

## Recommended Next Actions
3-7 ordered actions. Each with Why and Verification (the observable
signal that proves the action landed).

## Process Rules Worth Keeping
Optional. 0-5 paste-ready CLAUDE.md-style rules tied to concrete
failure patterns — or a single line saying none were extracted.

## Evidence Appendix
A. Decision timeline
B. Abandoned approaches & loops
C. Topic & focus map
D. Initial intent vs later stated state
+ sessions analyzed, source/confidence notes, omitted/truncated
counters, privacy note, source map.
```

The main body is meant to be readable in five minutes. The Evidence
Appendix carries full citation anchors (`[YYYY-MM-DD HH:MM /
sessShort / line:N]`), confidence labels (`direct` / `inferred` /
`summary-derived` / `external`), and the detailed archaeology — all
referenced from the body via compact `(evidence: A1, B2)` shorthand.
Tooling/meta-work (plugin setup, agent configuration) is filtered out
of the main body unless it materially impacted project work.

## How `/retro` works under the hood

1. Resolves the project root via `git rev-parse --show-toplevel`. Fails
   cleanly outside a git repo.
2. Resolves the report language: reads
   `<!-- retro-language: <code> -->` from the most recent report in
   `<repo>/.retro/`, or asks the user when no prior report exists.
3. Runs the extractor (`scripts/extract_sessions.py`):
   - Discovers all session JSONLs that belong to this project,
     including subdirectory-launched sessions, Claude worktrees, and
     subagent threads.
   - Streams JSONL line-by-line; walks nested `message.content[]`
     correctly (no flat-parse confusion between `tool_use` and
     assistant text).
   - Skips `thinking` blocks (counts only) and never emits `signature`
     fields.
   - Redacts API keys, GitHub PATs, AWS keys, JWTs, `Authorization:`
     headers; drops oversized pasted blocks.
   - Caps total evidence at 320 KB (~80K tokens); subagent transcripts
     get a sub-budget so they cannot drown the main user-assistant
     decision narrative.
4. Hands the curated evidence pack to the model, which writes the
   Markdown retrospective following `references/report-prompt.md`.
5. Writes the report to `<repo>/.retro/<YYYY-MM-DD>-retro.md` and
   creates `<repo>/.retro/.gitignore` (with `*.md`) on first run so
   reports stay out of git by default.

## Project layout the skill creates

```
<repo>/.retro/
├── .gitignore               # auto-created with *.md, on first run
├── 2026-05-09-retro.md      # today's report
└── 2026-05-09-retro-2.md    # second run today (suffix incremented)
```

That is everything — there are no other files. To reset the project's
retro state and trigger the first-run language question again, delete
the entire `.retro/` directory.

## Design notes

- **Extractor-first.** The riskiest part is JSONL parsing, not the
  prompt. The Python parser is deterministic, stdlib-only, and
  unit-tested (`scripts/test_extract_sessions.py`).
- **Bounded evidence.** A character budget is enforced before the model
  ever sees the pack. The model receives a curated digest, not raw
  logs.
- **Citations on findings.** Every entry in appendix sections A and B
  must carry an inline anchor. Optional Process Rules in the main body
  must point at a concrete A/B/C/D finding via compact reference; rules
  with no anchor are dropped, and the report says so plainly.
- **Privacy by default.** Reports are gitignored. Pasted blocks larger
  than 4 KB are dropped. Common secret patterns are redacted in the
  evidence pack.
- **Sidechain capped.** Subagent transcripts are tagged and their share
  of the evidence budget is hard-capped, so they cannot drown the main
  user-assistant decision narrative.
- **Language pinned per project.** The language for a project lives
  inside the most recent report as
  `<!-- retro-language: <code> -->`. To change it, edit that comment
  in the most recent report, or delete the `.retro/` directory and
  rerun `/retro`.

## Run the parser tests

```
python3 plugins/retro/scripts/test_extract_sessions.py
```

The tests cover parser shapes (nested `message.content[]`), redaction
patterns, budget allocation including the sidechain sub-budget, and
session discovery across worktrees and subagent threads.

## Limitations

- MVP: no chunking, no continuous retro, no cross-project view.
- Worktree directory pattern recognised:
  `<flat-root>--claude-worktrees-*`.
- Tested on macOS with default Python 3 (3.9+); should work anywhere
  stdlib `subprocess`, `pathlib`, `re`, `json` are available.
