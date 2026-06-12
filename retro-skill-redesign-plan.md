# Retro Skill Redesign Plan

## Purpose

Rework the existing `/retro` skill into one human-useful retrospective skill.

The current skill is strong at evidence-based conversational archaeology: it reconstructs decision history from Claude Code session JSONLs with citations, confidence markers, and source maps. That is valuable, but the generated report reads more like a forensic decision audit than a retrospective. The redesign should keep the evidence discipline while changing the primary output into a readable, actionable project retrospective.

The final skill should help a project owner quickly answer:

1. What actually happened in this project?
2. What worked?
3. What failed, stalled, or looped?
4. What is still unresolved?
5. What should I do next?

## Core Product Decision

`/retro` should default to a reader-first retrospective, not a chronology-first decision archive.

Decision archaeology remains an input method and appendix layer. It should not dominate the main report.

## Current Problem

The current report prompt optimizes for:

- explicit decision timeline;
- abandoned approaches and loops;
- topic/focus mapping;
- intent-vs-state comparison;
- CLAUDE.md rules derived from failure patterns;
- citation completeness and confidence labels.

This creates reports that are accurate but hard to read. The generated output exposes too much of the evidence machinery in the main body: dates, anchors, confidence values, source maps, and appendix-style detail. It also allows tooling/meta-work to compete with project work, even when the user asked for a project retrospective.

## Desired Output Shape

The main report should be readable in five minutes without opening the appendix.

Recommended structure:

```markdown
# Retrospective: <project-name>

Generated: <date>
Project root: <path>
Sessions analyzed: <n>
Date range: <date> to <date>

<!-- Privacy warning -->

## TL;DR
3-5 short sentences. Include the main project conclusion and the most important next decision.

## What Happened
Short narrative grouped by meaningful phases, not a full event list.

## What Worked
2-5 concise bullets. Focus on practices, decisions, or workflows that helped.

## What Did Not Work
2-5 concise bullets. Focus on failure patterns, stalls, repeated loops, or avoidable friction.

## Open Loops
A short list of unresolved threads, each with current status and why it matters.

## Recommended Next Actions
3-7 concrete actions, ordered by importance. Each action should be checkable.

## Process Rules Worth Keeping
Optional. 0-5 paste-ready CLAUDE.md-style rules, only if strongly supported by evidence.

## Evidence Appendix
Detailed decision timeline, abandoned approaches, citations, confidence notes, omissions, privacy counters, and source map.
```

The appendix may retain the current A/B/C/D/F evidence structure, but the main body should synthesize it.

## Non-Goals

- Do not turn `/retro` into a git-log summarizer.
- Do not perform a full codebase audit unless evidence already contains verifiable code/test outputs.
- Do not optimize for team sprint retrospectives, meeting agendas, or incident postmortems.
- Do not make CLAUDE.md rules the main product.
- Do not remove evidence discipline; move most of it out of the main reading path.

## Redesign Requirements

### 1. Reader-First Stance

Replace the current "archaeologist, not a judge" stance with a more balanced stance:

> You are a retrospective facilitator using conversational archaeology as evidence. Your job is to synthesize what happened into useful learning and next actions. Be evidence-grounded, but optimize the main report for human readability.

The skill should still avoid blame and unsupported claims.

### 2. Project Work vs Tooling Work

The report must separate project work from meta/tooling work.

Tooling events should be summarized only when they affected project outcomes. Otherwise, put them in a short "Tooling Side Notes" appendix entry or omit them from the main body.

Example rule:

> If an event is about installing, configuring, or debugging the agent/tooling itself, classify it as tooling/meta-work. Mention it in the main report only if it changed, blocked, or redirected project work.

### 3. Evidence Density Control

The main report should use compact evidence references such as `(evidence: B1, C2)` rather than full inline anchors.

Full anchors like `[2026-02-22 16:24 / agent-ab / line:86]` should live in the appendix.

### 4. Actionability

Every retrospective must include `Recommended Next Actions`.

Each action should include:

- action;
- why it matters;
- expected verification signal.

Example:

```markdown
1. Decide whether to continue or close `refactor/structure`.
   Why: the DI refactor is the main unresolved project loop.
   Verification: branch is either deleted/closed with notes or has a scoped follow-up plan with passing tests.
```

### 5. Unresolved Thread Detection

The report must explicitly call out unresolved work.

An unresolved thread is any topic that appears to have been started, paused, redirected, or abandoned without evidence of closure.

Each unresolved thread should include:

- current known state from the evidence;
- blocker or uncertainty;
- recommended decision.

### 6. Optional Process Rules

The existing section F should become optional and secondary.

Only include process rules when:

- there is a concrete repeated failure pattern;
- the rule is paste-ready;
- the rule is likely to prevent the same failure in future sessions.

Otherwise, say:

> No strong process rules were extracted from this run.

## Proposed Implementation Plan

### Phase 1: Update the Report Prompt

Primary file:

- `plugins/retro/skills/retro/references/report-prompt.md`

Tasks:

1. Change the stance from pure archaeology to retrospective facilitation.
2. Replace the required report sections with the reader-first structure.
3. Move detailed A/B/C/D/F-style evidence into `Evidence Appendix`.
4. Add explicit instructions for separating project work from tooling/meta-work.
5. Add required `Open Loops` and `Recommended Next Actions` sections.
6. Add guidance that the main report should be readable in five minutes.
7. Keep the language contract and citation discipline, but change citation placement.

### Phase 2: Update Skill Description and Body

Primary file:

- `plugins/retro/skills/retro/SKILL.md`

Tasks:

1. Update the skill description so it promises a project retrospective, not only decision history.
2. Keep trigger coverage for "decision history", "abandoned approaches", and "loops", because those remain valid inputs.
3. Make the output description match the new structure.
4. Avoid over-describing workflow in the YAML description; keep it focused on when to trigger.
5. Verify the target output path described in `SKILL.md` matches actual behavior and README.

### Phase 3: Update README

Primary file:

- `plugins/retro/README.md`

Tasks:

1. Explain that `/retro` produces a human-readable retrospective backed by session evidence.
2. Show the new output structure.
3. Clarify that detailed decision archaeology is in the appendix.
4. Clarify that tooling/meta-events are separated from project work.

### Phase 4: Update Evaluation Set

Primary files:

- `plugins/retro/eval/trigger-eval.json`
- `plugins/retro/eval/README.md`

Tasks:

1. Add positive examples asking for human-readable retrospectives, next actions, and unresolved loops.
2. Keep positive examples for decision history and abandoned approaches.
3. Add negative examples for sprint retrospectives, git summaries, and generic CLAUDE.md updates.
4. Add at least one regression case where the user asks for "not a forensic report, just tell me what matters and what to do next".

### Phase 5: Optional Extractor Review

The extractor is probably not the main bottleneck for this redesign. Review only for support gaps:

- whether source kinds (`main`, `sidechain`, `worktree`) are exposed clearly enough;
- whether stats allow the report to state when sidechain evidence dominates;
- whether tooling/meta classification should be prompt-only or extractor-assisted.

Avoid large extractor changes unless the report prompt cannot reliably classify evidence.

## Verification Methodology

Verification should check both correctness and usefulness.

### 1. Golden Report Comparison

Use the existing VideoGrabberBot run as the first golden fixture.

Baseline behavior:

- report is accurate but too forensic;
- project work and tooling work compete for attention;
- next actions are implicit rather than central;
- source detail dominates the reading experience.

Expected new behavior:

- first page identifies the DI refactor as the main unresolved project loop;
- successful xfail cleanup is listed under "What Worked";
- failed/incomplete DI refactor is listed under "What Did Not Work" and "Open Loops";
- Claude Code marketplace/plugin setup is classified as tooling/meta-work and does not dominate the main report;
- next actions explicitly recommend deciding the fate of `refactor/structure`;
- detailed anchors and source map are in the appendix.

### 2. Human Readability Rubric

Score each generated report from 1 to 5:

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Main conclusion clarity | Hard to identify | Present but buried | Clear in TL;DR |
| Actionability | No concrete next steps | Some vague suggestions | Checkable ordered actions |
| Evidence discipline | Unsupported claims | Mostly supported | Evidence-backed with appendix anchors |
| Readability | Forensic/log-like | Mixed | Readable in 5 minutes |
| Project/tooling separation | Mixed together | Partially separated | Clearly separated |
| Open-loop detection | Missing | Some threads found | Main unresolved threads are explicit |

Minimum acceptable score: 4 on every criterion for the golden fixture.

### 3. Output Contract Checks

For every generated report:

- has `TL;DR`;
- has `What Happened`;
- has `What Worked`;
- has `What Did Not Work`;
- has `Open Loops`;
- has `Recommended Next Actions`;
- has `Evidence Appendix`;
- main body uses compact evidence references or finding IDs, not dense raw anchors;
- appendix includes full citations and confidence notes;
- privacy note remains present;
- language contract is respected.

### 4. Evidence Integrity Checks

For every material claim in the main body:

- it must be supported by an appendix finding or direct citation;
- unsupported speculation must be labeled as uncertainty;
- no claim may say the current codebase is in a given state unless evidence includes command output, file content, git metadata, or another verifiable artifact.

### 5. Trigger Evaluation

Re-run the existing trigger evaluation after updating the skill description.

The skill should trigger for:

- "give me a project retrospective from my Claude Code sessions";
- "what worked, what failed, what should I do next";
- "what did we abandon or loop on";
- "why did we choose X";
- "extract project-specific CLAUDE.md rules from actual failures".

The skill should not trigger for:

- team sprint retro agendas;
- git log summaries;
- direct code reviews;
- generic CLAUDE.md editing;
- new project bootstrapping.

### 6. Regression Scenarios

Create or reuse at least three test fixtures:

#### Scenario A: Small Clean Project

Evidence shows one clear feature implementation, one small test fix, no major loops.

Expected:

- short report;
- no invented drama;
- `Open Loops` may say none found;
- process rules optional or absent.

#### Scenario B: Thrashing Project

Evidence shows repeated switches between approaches and unresolved work.

Expected:

- loops are surfaced early;
- next actions force decisions;
- timeline is summarized, not exhaustively listed in the main body.

#### Scenario C: Tooling-Heavy Session

Evidence contains mostly agent/plugin/tooling setup with little project code work.

Expected:

- report says project evidence is thin;
- tooling is classified separately;
- main project conclusions are conservative;
- no fake project retrospective is invented.

## Acceptance Criteria

The redesign is complete when:

1. A generated report is useful to a project owner without reading the appendix.
2. The main body is synthesis-first and action-oriented.
3. Detailed archaeology remains available in the appendix.
4. Tooling/meta-work no longer dominates project retrospectives.
5. Every material claim remains traceable to evidence.
6. The skill description still triggers correctly on decision-history use cases.
7. The VideoGrabberBot fixture produces a report whose main recommendation is obvious: decide the fate of the unfinished DI refactor.

## Recommended First Patch

Start with `report-prompt.md`.

Do not begin with extractor changes. The current bad output is primarily a prompt/product-shape problem, not a parsing problem.

After the report prompt produces a better VideoGrabberBot retrospective, update `SKILL.md`, README, and trigger evals to match the new product contract.

