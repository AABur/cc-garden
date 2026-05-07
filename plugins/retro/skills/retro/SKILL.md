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
The chosen report language is recorded inside each report as an HTML comment
(see Step 2 for how it is read on subsequent runs).

The report opens with a synthesis layer (TL;DR, What Happened, What Worked,
What Did Not Work, Open Loops, Recommended Next Actions, optional Process
Rules) and finishes with an Evidence Appendix that preserves the detailed
A/B/C/D archaeology, omission counters, and privacy notes.

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

The chosen language for a project lives **inside the project's most recent
report**, not in a separate file. Each report carries an HTML comment near
the top of the form:

```
<!-- retro-language: ru -->
```

Resolution:

1. **Look for existing reports** in `<project-root>/.retro/`. List files
   whose names match `<YYYY-MM-DD>-retro*.md` (e.g. `2026-05-07-retro.md`,
   `2026-05-07-retro-2.md`). Pick the most recent one: sort by the date in
   the filename descending; among files with the same date, take the one
   with the highest `-N` suffix (treat the unsuffixed `-retro.md` as the
   lowest, so `-retro-2.md` wins over `-retro.md` for the same date).
2. **Read the language tag** from that file. Scan the first ~10 lines for
   a line of the form `<!-- retro-language: <code> -->`. If found, take
   the lowercase ISO code, strip surrounding whitespace, and use it as
   the language for this run. **Skip the rest of Step 2 (do not ask the
   user) and proceed to Step 3 — Run the extractor.**
3. **If no report exists, or no tag is found in the most recent report,
   ask the user explicitly** via `AskUserQuestion`. Do **not** inspect
   `$LANG`, the user's chat language, or session content — language
   choice for retros is a deliberate per-project decision, not a guess.

   - Question: `What language should /retro use for this project's retros?`
   - Header: `Retro language`
   - Option 1:
     - `label: "English"`
     - `description: All future /retro reports for this project will be in English.`
   - Option 2:
     - `label: "Other language"`
     - `description: Pick another language — you'll specify it in the next message.`

4. **Resolve the choice**:
   - If the user chose `English`, set the language to `en` and continue.
   - If the user chose `Other language`, send one short follow-up message
     in the chat asking the user to name the language they want. Accept
     any of: an autonym (`Русский`, `Deutsch`, `日本語`), the English
     name (`Russian`, `German`, `Japanese`), or an ISO-639-1/2 code
     (`ru`, `de`, `ja`). Read the user's reply and normalize it to a
     lowercase ISO-639 code yourself — for common languages a short
     mental mapping is enough (`Русский`/`Russian`/`ru` → `ru`,
     `Deutsch`/`German`/`de` → `de`, `日本語`/`Japanese`/`ja` → `ja`,
     `中文`/`Chinese`/`zh` → `zh`, `Español`/`Spanish`/`es` → `es`,
     `Français`/`French`/`fr` → `fr`, etc.). If the user typed an
     ISO-639 code already, accept verbatim (lowercased). If the input
     is genuinely ambiguous, ask **one** more clarifying question;
     otherwise pick the obvious mapping. Use that code as the language
     for this run.

There is no separate marker file. The resolved language code is passed to
the report-prompt instructions in Step 4; the new report's header includes
the `<!-- retro-language: <code> -->` comment, which becomes the source of
truth for the next run.

To change the language for a project, the user edits the comment in the
most recent report (or deletes that report) and runs `/retro` again.

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
- Do not include generic CLAUDE.md rules in the Process Rules section. If
  a rule cannot be tied to a concrete A/B/C/D finding in the Evidence
  Appendix, omit it — the explicit "no strong process rules were
  extracted from this run" line is the correct outcome for an empty
  section.
- Do not auto-detect the report language from session content, `$LANG`,
  or the user's chat language. The language is recorded in the
  `<!-- retro-language: <code> -->` HTML comment inside each report. To
  change it for a project, the user edits the comment in the most recent
  report or deletes that report.
- Do not mix languages within the report. The chosen language applies to
  the entire narrative; only identifiers stay verbatim.
