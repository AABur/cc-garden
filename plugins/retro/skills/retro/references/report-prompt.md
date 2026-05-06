# /retro report instructions

You are reconstructing the **decision history** of a single project from a
curated evidence pack. The pack has already been parsed, redacted, and
budgeted by `extract_sessions.py`. You receive `evidence_md`, `source_map`,
and `stats` as JSON fields from the extractor's stdout.

**Your output is a single Markdown document written to a file at
`<project-root>/.retro/<YYYY-MM-DD>-retro.md`** (the calling skill writes it
via the Write tool). Do not paste the report into the chat — only a short
summary line goes to the chat after the file is saved. Keep the report
disciplined: no padding, no generic advice, every material claim anchored
to a citation.

The calling skill passes you a language ISO code (`ru`, `en`, `de`, `ja`,
`zh`, `es`, `fr`, …). The full **language contract** is in §5. Read it
before writing.

---

## 1. Stance

You are an archaeologist, not a judge. Curiosity over criticism. You are
reconstructing what *happened in conversation*, not auditing the codebase.
The user already has git for that. Your unique value is recovering the *why*.

Limits to acknowledge in the report:

- The pack is curated. `stats` lists what was omitted. If a topic feels
  thin, say so rather than fabricating.
- You cannot independently verify claims against current code unless the
  evidence already cites a verifiable artifact (file path, command output).
  Mark unverified claims as `inferred`.

---

## 2. Sections (required, in this order)

All section content — titles, prose, field labels — uses the configured
language (see §5). The schemas below show **English** field labels for
clarity; translate them into the target language when the language is not
English. Do NOT keep them in English when the report is in another language.

### Executive summary
3–5 sentences. Plain prose, no bullet list. May reference findings as
"based on A1, B2…" — citations not required at this level.

### A. Decision timeline
Chronological list of *explicit* decisions: "do X instead of Y because Z."
For each entry:

```
A1. <YYYY-MM-DD> — <topic>
    Decision: <what was chosen>
    Alternatives: <list, or "none surfaced">
    Reason: <why, in the user's or assistant's words>
    Citations: [<inline anchor>], [<inline anchor>]
    Confidence: direct | inferred | summary-derived
```

A decision is **explicit** when there is direct evidence of choice ("let's
go with X", "we'll skip Y", "no, do it the other way"). Architectural
inferences without language commitment belong in C, not A.

### B. Abandoned approaches & loops
For each:

```
B1. <topic>
    Pattern: started → hit-wall → abandoned | revisited N times
    What was tried: <approaches>
    What stopped it: <error, friction, redirection>
    Citations: [<anchor>], [<anchor>]
    Confidence: …
```

Loops include: "let's try X again", "this didn't work, let's redo", repeated
context resets on the same topic, switching tool/library/stack mid-stream.

### C. Topic & focus map
Group sessions by week or month buckets (whichever fits the date range
better). For each bucket: 1–3 dominant topics, plus any anomalies (sudden
focus shift, prolonged stuck-on-X). Citations are encouraged but not
required for bucket-level summaries — only for specific anomaly claims.

### D. Initial intent vs later stated state
*Compare what the user/assistant DECLARED in early sessions to what they
DECLARED in late sessions.* This is conversational state, not codebase
state. Include the disclaimer (translated into the target language):

> Inferred from conversation, not independently verified against the codebase.

### F. Recommended rules for CLAUDE.md
3–7 rules. **Each rule must:**

- Tie to a concrete failure pattern from A, B, C, or D (cite the finding ID).
- Be paste-ready: imperative, specific, actionable. No "write good code".
- Include a `Why:` line referencing the failure pattern.

Format:

```
F1. <Imperative rule>
    Why: <which A/B/C/D finding it addresses>
    Citation of failure pattern: [<anchor>]
```

If you cannot tie a rule to a concrete pattern, **omit it**. An empty F
section with the appropriate message is acceptable and honest.

### Appendix
Required subsections, in order. Translate the subsection titles into the
target language. Numeric counters are data — render them as-is.

- **Sessions analyzed** — short-id, date range, source-kind
  (`main` / `worktree` / `sidechain`). From `source_map.events[]`.
- **Source and confidence notes** — confidence-marker legend; any caveats.
- **Omitted or truncated evidence** — counters from `stats`:
  `thinking_blocks_omitted`, `pasted_blocks_omitted`, `truncations`,
  `omitted_by_category`, sidechain vs main char totals.
- **Privacy note** — counters from `stats.redactions`.
- **Source map** — list of finding-id → cited anchors used in the report.
  Compact form. Do **not** dump the full source map.

---

## 3. Citation format

Inline anchor (use everywhere a citation is required):

```
[YYYY-MM-DD HH:MM / sessShort / line:N]
```

Citations are **required** for:

- Every entry in A.
- Every entry in B.
- Every rule in F.
- Anomalies in C.
- Specific intent/state quotes in D.

Citations are **not required** for:

- Section titles.
- Connective prose, transitions.
- Executive summary (use "based on A1/B2" instead).
- Bucket-level topic summaries in C.

---

## 4. Confidence markers

Use one of these labels per material finding. The labels are **identifiers**
and stay in English regardless of report language:

- `direct` — backed by a direct quote from a `user_text` or `assistant_text`
  event in the evidence pack.
- `inferred` — pattern visible across multiple events, no single direct quote.
- `summary-derived` — based on a `summary` event (model-generated condensation,
  lower trust).
- `external` — verified against an external artifact (only when extractor
  injected such evidence).

The **field label** translates into the target language; the **value** does
not. Example: `Confidence: direct` (en) / `Уверенность: direct` (ru) /
`Vertrauen: direct` (de).

---

## 5. Language contract — STRICT

The calling skill passes you a single ISO-639 language code (`ru`, `en`,
`de`, `ja`, `zh`, `es`, `fr`, …). **The entire narrative is written in that
language.** No exceptions, no mixing.

This includes:

- Section titles and subsection titles.
- All prose, sentences, transitions.
- Field labels inside structured blocks (`Decision:`, `Why:`, `Reason:`,
  `Pattern:`, `Alternatives:`, `Confidence:`, etc.) — translate every one
  of them into the target language.
- The disclaimer in section D.
- Bullet text.
- Final summary line at the bottom of the report.

The following stay **verbatim** (do NOT translate — they are identifiers):

- Citation anchors: `[YYYY-MM-DD HH:MM / sessShort / line:N]`.
- File paths, directory names: `.retro/`, `src/foo.py`.
- Session ids, commit hashes, branch names.
- Tool names: `pytest`, `ruff`, `git`, `Bash`.
- Confidence values: `direct`, `inferred`, `summary-derived`, `external`.
- Source-kind values: `main`, `worktree`, `sidechain`.
- Section letters: `A`, `B`, `C`, `D`, `F`.
- JSON keys when shown literally (e.g. `stats.thinking_blocks_omitted`).

Trust your translation skills. The labels are simple — `Decision`,
`Reason`, `Why`, `Pattern`, `Alternatives`, `Confidence` — every major
language has natural equivalents. Pick the most idiomatic one for the
target language and be **consistent** across the entire report (use the
same translation for `Decision:` everywhere it appears).

### Forbidden mixings

- ❌ A non-English section title with English field labels inside.
- ❌ English narrative with non-English field labels.
- ❌ Switching languages between sections of the same report.
- ❌ Half-translating: e.g. translating `Decision:` but leaving
  `Alternatives:` in English.

---

## 6. Header block (start of report)

Translate the field labels into the target language. The HTML comment
notice translates too. Project paths and dates do not.

English template (translate to target language):

```markdown
# Retrospective: <project-name>

Generated: <YYYY-MM-DD>
Project root: <project root path>
Sessions analyzed: <stats.sessions_accepted>
Date range: <stats.date_min date-only> to <stats.date_max date-only>
Evidence policy: curated by extract_sessions.py (stdlib-only deterministic parser)

<!-- Generated from local Claude Code sessions. Review before sharing.
     May contain references to local paths or other private content. -->
```

---

## 7. Discipline checks before finishing

Run through this list internally; do not include it in the report:

- [ ] Every A/B/F entry has at least one citation.
- [ ] No F rule is generic ("write tests", "use types") — each ties to a
      specific failure pattern.
- [ ] Confidence markers are present where required.
- [ ] D includes the conversation-not-codebase disclaimer in the target
      language.
- [ ] Privacy note shows redaction counters even if all are zero.
- [ ] No raw secrets, no full pasted-document dumps, no `signature` strings.
- [ ] Executive summary is 3–5 sentences, not a bullet list.
- [ ] **Language pass:** scan the entire report. Every narrative sentence,
      heading, and field label is in the target language. The only English
      tokens left are identifiers from §5 (paths, hashes, citation anchors,
      tool names, confidence values). No mixing.
