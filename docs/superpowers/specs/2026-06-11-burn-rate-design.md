# burn-rate — Design Spec

**Date:** 2026-06-11
**Status:** Approved (brainstorming → spec)
**Author:** Alexander Burchenko
**Credits:** Concept and leak taxonomy adapted from [`token-audit`](https://github.com/BayramAnnakov/token-audit-skill) by Bayram Annakov. Code is an independent, from-scratch implementation.

---

## 1. Context & Problem

`token-audit` (BayramAnnakov) audits Claude Code token spend by parsing local
JSONL transcripts, inventorying config, running `ccusage` for a baseline, and
flagging ranked leaks. It is well-architected and privacy-respecting, but a
review surfaced concrete, verified defects that limit trust in its numbers:

- **Stale pricing.** `cost_model.py` prices Opus at **$15/$75** — the *previous*
  Opus generation. Current Opus 4.6/4.7/4.8 is **$5/$25**. The lineup also gained
  Fable 5 ($10/$50, new tokenizer ~+30% tokens) and Haiku 4.5 ($1/$5); current
  1M-context models carry **no long-context premium**.
- **No deduplication.** `jsonl_parser._accumulate()` sums `usage` for every
  assistant line with no `(message.id, requestId)` key, while `ccusage`
  deduplicates. Result: the `model_selection` detector reports **$672** for a
  *subset* of turns while `ccusage` reports **$171** for the *entire* week of
  Opus — the subset exceeds the superset, proving overcount.
- **Weak heuristic.** `model_selection` flags any Opus turn with `<1000` output
  tokens as "could have been Sonnet" — output length is a poor proxy for task
  difficulty, and it is blind to workflow/subagent model inheritance (the actual
  dominant sink in real usage).
- **Confirmation friction.** The skill gates fix application behind many per-fix
  prompts; for a read-only audit this is unnecessary nagging.
- **Ignored signal.** Real transcripts carry rich attribution
  (`attributionSkill/Plugin/McpServer/Agent`, `sessionKind`, `isSidechain`,
  `apiErrorStatus`, `cache_creation` 5m/1h split, `service_tier`) that
  `token-audit` does not read.

`burn-rate` is a clean-room rewrite that keeps the proven leak taxonomy and
honest subscription framing, fixes the defects above, and exploits the ignored
signal — while running **read-only** with **zero confirmation prompts**.

### Verified facts (checked on this machine, 2026-06-11)

- `costUSD` is **absent** from local JSONL (0/434 assistant turns scanned) →
  cannot rely on a pre-computed cost field; baseline `$` must come from `ccusage`.
- `requestId` and `message.id` present in **100%** of assistant turns → dedup key
  is available.
- `ccusage` (now `ccusage/ccusage`, ~16k★, Rust) default cost mode is `auto`:
  uses JSONL `costUSD` when present, else computes from token counts against an
  embedded LiteLLM snapshot **optionally refreshed online at runtime**
  (`--offline` skips refresh). Pricing overrides live under
  `defaults.pricingOverrides` in its config.

## 2. Goals / Non-Goals

**Goals**
- Read-only token-spend diagnosis for Claude Code, ranked by impact.
- Accurate baseline via `ccusage --json`; accurate detector estimates via a
  current (2026) price snapshot with per-bucket rates.
- Deduplicated, attribution-aware transcript analysis.
- Honest framing: lead with tokens reclaimed and % category reduction; dollars
  parenthetical and labeled "reference only — flat-fee subscription".
- Coverage ≥ `token-audit`, plus new detectors the rich signal enables.
- Ship into the `cc-garden` marketplace; run alongside `token-audit` for A/B.

**Non-Goals**
- No fix application. The skill never edits `settings.json`, `CLAUDE.md`, hooks,
  or skills. (Mode: **diagnostics only**.)
- No writing to disk at all — report goes to chat only.
- No network calls except the single optional `ccusage` invocation.
- Not a continuous tracker (that is `ccusage`/dashboards); this is a point-in-time
  audit.
- v1 scopes to Claude Code; other assistants (Codex) are segregated, not analyzed.

## 3. Architecture

Python **stdlib only** (matches `lucky-break`/`retro`), orchestrator emits JSON,
the skill body narrates in the user's language.

```
plugins/burn-rate/
├── .claude-plugin/plugin.json
├── LICENSE                       # MIT, dual copyright (B. Annakov + A. Burchenko)
├── README.md                     # badges, install, usage, Credits
└── skills/burn-rate/
    ├── SKILL.md                  # read-only; allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py *) Read Grep ; disallowed-tools: Edit Write
    ├── scripts/
    │   ├── audit.py              # orchestrator → JSON to stdout
    │   ├── jsonl_parser.py       # dedup + rich attribution + cache 5m/1h split
    │   ├── ccusage.py            # ccusage --json wrapper (online auto), graceful fallback
    │   ├── pricing.py            # 2026 snapshot, per-bucket + service_tier; optional pricingOverrides
    │   ├── config_inspector.py   # settings/hooks/skills/MCP/plugins inventory
    │   ├── attribution.py        # tokens by skill/plugin/mcp/agent/sessionKind/branch
    │   ├── detectors/
    │   │   ├── __init__.py        # Leak dataclass + registry
    │   │   └── <detector>.py      # one module per detector
    │   └── test_*.py             # stdlib unittest, standalone-runnable
    └── references/
        ├── leak-taxonomy.md      # own taxonomy (built on original + new)
        ├── pricing-2026.md       # price snapshot with date + source
        └── techniques.md         # 2026 token-engineering levers
```

### Module contracts

- **`jsonl_parser`** — walks `~/.claude/projects/**/*.jsonl`, two-stage time
  filter (mtime + per-turn timestamp), **dedup set keyed on
  `(message.id, requestId)`** before accumulating `usage`. Extracts: model,
  usage buckets (`input`, `output`, `cache_read`, `cache_creation` split into
  `ephemeral_5m`/`ephemeral_1h` when present), `service_tier`, tool calls,
  hook events, file reads, and attribution fields (`attributionSkill`,
  `attributionPlugin`, `attributionMcpServer`, `attributionMcpTool`,
  `attributionAgent`, `agentId`, `sessionKind`, `isSidechain`, `gitBranch`,
  `apiErrorStatus`, `isApiErrorMessage`). Privacy: sizes/counts/names only, no
  payloads; Bash commands reduced to first token.
- **`ccusage`** — runs `ccusage daily --since --until --json` (online `auto`
  mode for fresh prices + dedup). On missing Node/ccusage or failure: returns
  `None` + error string; audit proceeds and the report notes the absence.
- **`pricing`** — 2026 per-million table with buckets
  `input / output / cache_write_5m (1.25×) / cache_write_1h (2×) / cache_read
  (0.1×)`, `service_tier` aware, per-model **cacheable minimum** (4096 Opus /
  2048 Sonnet·Fable / 1024 Sonnet 4.5). Resolves model IDs to the 2026 lineup;
  no Opus fallback for unknown models (returns explicit "unknown" rather than
  mispricing). Optionally reads `ccusage` `defaults.pricingOverrides`.
- **`attribution`** — aggregates deduped tokens by skill / plugin / mcp / agent /
  `sessionKind` (interactive vs workflow vs subagent) / branch → the Pareto
  "where to look first" view.
- **`detectors/*`** — each exposes `detect(sessions, config, pricing) -> list[Leak]`.
  `Leak` carries `est_weekly_tokens` (primary), `est_weekly_cost_usd`,
  `est_weekly_savings_usd` (ranking only), severity, evidence, fix_action (text).
- **`audit.py`** — runs ccusage, parser, config inventory, attribution, all
  detectors (error-isolated), ranks leaks, emits JSON.

## 4. Detectors — phased delivery (vertical slices)

Each phase is its own PR with green tests.

**Phase 1 — core / MVP**
- Skeleton, `jsonl_parser` (dedup + attribution), `ccusage` wrapper, `pricing`
  snapshot, `config_inspector`, `attribution` Pareto.
- Detectors: `model_selection*` (combined signal: output size + tool-call count +
  `isSidechain`/`agentId`/`sessionKind`, not output alone), `context_rot`
  (>400k zone), `cache` (with per-model cacheable-minimum awareness so sub-minimum
  prefixes are not blamed on the user; 5m/1h split), `claude_md_bloat` (current
  target, flagged "cited, not re-confirmed for 2026"; non-English tax note).
- Report + tests. **Run and compare against `token-audit`.**

**Phase 2 — parity with original**
- `hook_bloat`, `skill_descriptions`, `bash_antipatterns`, `file_reads`,
  `recurring_scripts`, `tool_schema`.

**Phase 3 — new detectors (enabled by ignored signal)**
- `subagent_fanout` — workflow/subagent token multiplier via
  `sessionKind`/`isSidechain`/`agentId` (direct answer to the dominant sink).
- `effort_audit` — Sonnet 4.6 silently defaults to `high` effort.
- `error_retries` — token waste from `apiErrorStatus`/retry turns (revives the
  abandoned Sniffly angle).
- `cache_invalidators` — heuristic for silent cache-prefix invalidation
  (`cache_read` stays 0 across similar prefixes; sub-minimum prefix on Opus).

## 5. Pricing strategy

- **Baseline `$`** → `ccusage --json` (online `auto`): fresh LiteLLM prices,
  dedup, multi-agent. Authoritative for the spend summary.
- **Detector estimates** → local `pricing.py` 2026 snapshot (ccusage gives no
  per-leak breakdown). Per-bucket rates incl. 5m vs 1h cache-write and
  `service_tier`. Optionally overlay `ccusage` `pricingOverrides`.
- **`costUSD`** — not present in current local data; if a future Claude Code
  version writes it, prefer it (mirrors ccusage `auto`).
- **Never hard-code as the sole source** the way the original did; snapshot
  carries an explicit date + source and lives in `references/pricing-2026.md`.

## 6. Report (chat only, Russian for this user)

Sections: (1) Spend summary from ccusage; (2) Pareto "where to look first"
(by skill/plugin/agent/sessionKind — the new attribution view); (3) Ranked
leaks with severity, evidence (numbers), tokens reclaimed + % reduction,
parenthetical `$`, concrete fix text; (4) 1-3 user-specific brainstormed ideas;
(5) single highest-leverage action. Lead with tokens/headroom; dollars labeled
"reference only — flat-fee subscription". Default language English in SKILL.md,
switch to the user's conversation language (Russian here).

## 7. Privacy & safety

All local except the single optional `ccusage` call. Sizes/counts/names only;
no payloads, no secrets (Bash reduced to first token). Read-only: no Edit/Write;
nothing written to disk, not even the report.

## 8. Packaging & parallel run

- Register `burn-rate` in `.claude-plugin/marketplace.json` (name ≠ `token-audit`).
- `plugin.json`: name/description/author (cc-garden convention, no version field).
- A/B: invoke explicit slash commands `/burn-rate` vs `/token-audit`. Natural-
  language triggers will overlap between the two installed skills — that is
  acceptable; slash commands are unambiguous for comparison.
- **Credits:** MIT `LICENSE` with dual copyright (Bayram Annakov + Alexander
  Burchenko); attribution line atop `SKILL.md`; Credits section in `README.md`
  citing concept + taxonomy origin. Code is original.

## 9. Testing

- `stdlib unittest`, `test_*.py` beside sources, standalone-runnable
  (`python3 test_x.py`) and pytest-discoverable — matches repo convention.
- TDD: failing tests first per the user's workflow. Cover: dedup correctness,
  per-bucket pricing, model-ID resolution (incl. unknown → explicit unknown),
  cacheable-minimum logic, attribution aggregation, each detector's threshold.

## 10. Verification (end-to-end)

1. `python3 plugins/burn-rate/skills/burn-rate/scripts/audit.py --days 7` →
   valid JSON; detector_errors empty.
2. Cross-check baseline `$` against `ccusage daily --json` for the same window.
3. Confirm deduped Opus token total ≤ ccusage's Opus total (no overcount).
4. Run both `/burn-rate` and `/token-audit`; diff the reports; confirm
   burn-rate's numbers reconcile with ccusage where the original's did not.
5. All `test_*.py` green.

## 11. Open items / risks

- `claude_md_bloat` 2k-token target is cited but not re-confirmed against the
  live 2026 doc — flag in output, don't assert.
- Pricing snapshot will drift; mitigated by ccusage-for-baseline + dated snapshot,
  but needs periodic refresh (note in README).
- `cache_creation` sub-key names (`ephemeral_5m_input_tokens` etc.) to be
  confirmed against real data during Phase 1 parser work.
