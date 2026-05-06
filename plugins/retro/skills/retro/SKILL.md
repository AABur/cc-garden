---
name: retro
description: >-
  Reconstruct a project's decision history from local Claude Code session
  JSONLs and write the retrospective to a Markdown file in the project
  (`.retro/<YYYY-MM-DD>-retro.md`).

  Use when the user asks for a retrospective, project archaeology, decision
  history, abandoned approaches, or thrashing/loops analysis — based on
  conversation history with the agent in the current repository, not on
  git log or training-data knowledge.

  Trigger on: "/retro", "retrospective", "decision history", "project
  archaeology", "what did we abandon", "why did we choose X over Y",
  "why did we pick X", "when did we pivot", "what assumptions did we walk
  back", "show me the loops we hit", "what got dropped/scrapped". Also
  trigger when the user wants CLAUDE.md rules GENERATED FROM ACTUAL FAILURE
  PATTERNS in their session history — that is `/retro`'s section F output,
  not the generic claude-md-improver skill.

  Skip when: the question is about git log / commits (use git directly),
  about team sprint retros (different domain), or about updating an
  existing CLAUDE.md with new content (use claude-md-management).
---

# /retro — Project decision-history retrospective

Single-shot. Reads local Claude Code session JSONLs for the current git repo,
parses them deterministically via a Python extractor, and writes a
**Markdown report file** at `<project-root>/.retro/<YYYY-MM-DD>-retro.md`.
The report itself does not get printed into the chat — only a short summary
(path + counters) is shown. Open the file in your editor to read the full
report.

A `.retro/.gitignore` is auto-created so reports stay out of git by default.
A small per-project language marker also lives under Claude's home directory
(see Step 2).

The report has sections A (decision timeline), B (abandoned approaches &
loops), C (topic & focus map), D (initial intent vs later stated state), and
F (recommended rules for CLAUDE.md), plus a short appendix with citations
and privacy counters.

---

## Step 1 — Resolve the project root

```bash
git rev-parse --show-toplevel
```

If exit code is non-zero, tell the user:

> `/retro` requires a git repository. `cd` into the repo you want analysed
> and re-run.

Stop on failure. Do not try to extract sessions outside a git repo.

---

## Step 2 — Determine the report language

The chosen language persists per-project in a tiny one-line marker file under
Claude's home dir, **not** in the user's project. The path is:

```
~/.claude/projects/<flat-encoded-project-root>/.retro-language
```

`<flat-encoded-project-root>` matches Claude Code's own encoding: take the
absolute project root (from Step 1) and replace every character that is not
`[A-Za-z0-9-]` with `-`. Examples:

- `/Users/aabur/Documents/GitHub/AABur/cc-garden` → `-Users-aabur-Documents-GitHub-AABur-cc-garden`
- `/Users/aabur/Documents/GitHub/AABur/tgfolder_analyzer` → `-Users-aabur-Documents-GitHub-AABur-tgfolder-analyzer`

Resolution:

1. **Read the marker file** if it exists. The file contains a single ISO-639
   language code on the first line (e.g. `ru`, `en`, `de`, `ja`, `zh`).
   Strip whitespace. If non-empty, use that language and skip to Step 3.
2. **Otherwise, detect the user's likely native language** from the `LANG`
   environment variable. Run `echo "$LANG"` and take the prefix before the
   first `_` or `.`:
   - `ru_RU.UTF-8` → `ru`
   - `de_DE.UTF-8` → `de`
   - `ja_JP.UTF-8` → `ja`
   - `en_US.UTF-8` → `en`
   - empty / unset → `en`
3. **If detected language equals `en`**, no question is needed — silently
   write `en` into the marker file and continue.
4. **If detected language differs from `en`**, ask **exactly one** question
   via `AskUserQuestion`:

   - Question: `What language should /retro use for this project's retros?`
     (translate this question into the detected language for the second
     option's description if you want — but the question itself can stay in
     English, the user's chat language, or the detected language; pick what
     feels least intrusive)
   - Header: `Retro language`
   - Option 1:
     - `label: "English"`
     - `description: All future /retro reports for this project will be in English.`
   - Option 2:
     - `label: <Native name of the detected language>` — e.g. `Русский`,
       `Deutsch`, `日本語`, `中文`, `Español`, `Français`. Use the
       autonym, not the English name.
     - `description: <One-line description in that native language saying
       "All future /retro reports for this project will be in this
       language.">`

   Take the user's choice. Map back to ISO code (`English` → `en`,
   `Русский` → `ru`, `Deutsch` → `de`, etc.). Write the code into the
   marker file (one line, no trailing newline beyond `\n`). Continue with
   that language.

The marker file is a single line, always overridable: the user can edit it
or delete it any time to change the language for next run. Never overwrite
an existing marker — only create it on first run.

---

## Step 3 — Run the extractor

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/cc-garden/plugins/retro}/scripts/extract_sessions.py" \
  --project-root "$(git rev-parse --show-toplevel)" \
  --budget-chars 320000
```

The extractor is **read-only** — it does not write anything. It prints a
single JSON object to stdout. Parse it. Possible shapes:

- `{"status": "ok", "evidence_md": "...", "source_map": {...}, "stats": {...}, ...}` — proceed.
- `{"status": "no_sessions", "message": "..."}` — print the message and stop.
  Do **not** invent a retro from nothing.
- `{"status": "fail", "error": "..."}` — print the error and stop.

The extractor budgets evidence to ~320 KB of markdown (~80K tokens). It
already redacts API keys, GitHub PATs, AWS keys, JWTs, `Authorization:`
headers, drops large pasted blocks, skips `thinking` blocks and never emits
`signature` fields.

---

## Step 4 — Generate the retrospective and write it to a file

You now have:

- `evidence_md` — curated session evidence with citation anchors.
- `source_map.events[]` — index of events with full identifiers.
- `stats` — counters (omissions, redactions, dates, sessions count).

Read `references/report-prompt.md` (in this skill's directory). Follow it
exactly: section order, citation rules, confidence markers, language
contract.

Pass the language code from Step 2 to the report instructions. **The entire
narrative — section titles, prose, field labels — is in that single
language**, except identifiers (paths, sessionIds, hashes, citation
anchors, tool names, confidence values) which stay verbatim.

**Output target:**

```
<project-root>/.retro/<YYYY-MM-DD>-retro.md
```

If a file with that name already exists, append `-N` (e.g. `-2`, `-3`)
until the name is free. **Never overwrite an existing report.**

Procedure:

1. Run `mkdir -p <project-root>/.retro` (already in allow-list).
2. Ensure `<project-root>/.retro/.gitignore` exists with content `*.md`. If
   the file is missing, create it once via the Write tool. If it exists,
   leave it alone — the user may have customized it.
3. Generate the full Markdown report following `references/report-prompt.md`.
4. Write the report via the Write tool to the target path.
5. **Do not print the full report into the chat.**

---

## Step 5 — Print a short summary

After the file is written, print **only** a short confirmation to the chat,
in the report language. Format:

```
✓ <path/to/retro.md>

sessions: <stats.sessions_accepted>
period:   <stats.date_min date-only> → <stats.date_max date-only>
evidence: <stats.chars_included> chars (~<stats.estimated_tokens_included> tokens)
omitted:  main <stats.main_chars_omitted> / sidechain <stats.sidechain_chars_omitted>
language: <ru | en | de | …>
```

Do not paste any section of the report into the chat. The user opens the
file in their editor.

---

## What NOT to do

- Do not run if the user is not inside a git repository — fail clearly.
- Do not paste the report into the chat. The full report goes to the file;
  only the short summary from Step 5 goes to chat.
- Do not overwrite an existing report — append `-N` to the filename until
  free.
- Do not include `thinking` block content, `signature` fields, or
  `attachment` payloads in the report. The extractor strips them; do not
  re-introduce them from any source.
- Do not invent citations. Every anchor in the report must correspond to a
  real entry in `source_map.events[]`.
- Do not include generic CLAUDE.md rules in section F. If a rule cannot be
  tied to a concrete A/B/C/D finding, omit it.
- Do not auto-detect the report language from session content. The language
  is set once via Step 2 and stored in the marker file. To change it, the
  user edits or deletes the marker file.
- Do not mix languages within the report. The chosen language applies to
  the entire narrative; only identifiers stay verbatim.
