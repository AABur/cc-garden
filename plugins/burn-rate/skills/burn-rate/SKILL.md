---
name: burn-rate
description: >-
  Audit Claude Code token spend, read-only, and rank where tokens are leaking.
  Deduplicated transcript analysis with skill/plugin/MCP/agent attribution,
  current 2026 pricing, ccusage baseline, and concrete fixes — no config is ever
  modified and burn-rate writes no output files.

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
no settings, CLAUDE.md, hooks, or skills are modified, and burn-rate writes no
output files. All analysis is local; the only network call is the optional
`ccusage` baseline (which may create npm cache entries).

## What it measures

The audit builds three accounting ledgers from the local transcript store:

- **Spend ledger** — deduplicated assistant-turn usage (`message.id` +
  `requestId`). This is the primary cost basis. Duplicate records (cached
  tool-output echoes) are filtered out before pricing.
- **Causal ledger** — tool, hook, and user events parsed for attribution and
  workflow diagnosis. Estimates here identify *why* tokens were generated; they
  are not additive spend.
- **Workload ledger** — session-level metadata (volume, timing, parallelism)
  used to classify usage patterns.

> Primary cost basis is local deduplicated assistant usage. Tool, hook, and user
> events are parsed for attribution and workflow diagnosis only; their estimates
> are not additive spend unless explicitly reconciled.

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--days N` | 7 | Look-back window in days |
| `--skip-ccusage` | off | Skip the `ccusage` baseline entirely |
| `--ccusage-timeout N` | 25 | Seconds to wait for `npx ccusage` before aborting |

## Key output fields

| Field | Description |
|---|---|
| `accounting_basis` | Local deduplication stats: raw vs deduped records, sidechain count, event totals |
| `opportunity_ranking` | Ranked list of findings by `rank_signal_cost_usd` (descending). Not additive — entries may overlap. |
| `total_savings.status` | Always `"not_reported"` because ranking scopes overlap; no single total is meaningful |
| `reconciliation` | `ccusage` comparison status: `matched`, `skipped`, or `failed` |
| `leaks` | Individual findings, each with a `basis` field (`spend`, `causal`, `workload`, or `mixed`) |
| `bottlenecks` | Top consumers by skill / plugin / agent / session-kind (Pareto attribution) |

## Detectors

| id | ledger | what it catches |
|---|---|---|
| `model_routing:interactive_opus_simple` | spend | Opus on short interactive turns (excludes fan-out) |
| `model_routing:subagent_opus_simple` | spend | Opus on short background/subagent turns |
| `context:rot_zone` | spend | Turns past ~400k context |
| `cache:low_hit_ratio` | spend | Cache churn, cacheable-minimum aware |
| `claude_md:bloat` | spend | CLAUDE.md over ~2k tokens |
| `causal:hook_output_bloat` | causal | Hook stdout feeding oversized text into context |
| `causal:bash_antipatterns` | causal | Shell commands known to inflate output (cat large files, find /, etc.) |
| `causal:repeated_reads` | causal | Same file read 4+ times in a session with large content |
| `workload:high_volume_parallel_workload` | workload | Projects with high parallel session volume (>10 sessions/day) |
| `workload:possible_recurring_automation` | workload | Multi-signal: high volume + short sessions + no tool-search + many hooks |

## Workflow

### Step 1: Run the audit

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/audit.py" --days 7
```

`${CLAUDE_SKILL_DIR}` resolves to this skill's directory. If — and only if — the
command fails with "No such file or directory" (the variable did not expand),
locate the script with `find ~/.claude -path '*burn-rate*/scripts/audit.py' | head -1`
and run that path. Pass `--days N` to change the window (default 7).

To skip the ccusage baseline: `--skip-ccusage`.
To set a custom timeout: `--ccusage-timeout 30`.

### Step 2: Narrate the JSON as a report

Parse the JSON and write a tight report in the user's conversation language
(default English; for a Russian conversation, write the report in Russian — keep
technical terms like ccusage, /compact, CLAUDE.md, MCP untranslated).

Sections:
1. **Spend summary** — from `ccusage` (total, by model, trend). If `ccusage_error`
   is set, say so and proceed with token counts only. If `parser_errors` is
   non-empty, warn that some transcripts were skipped or partially unreadable, so
   the totals below may be incomplete.
2. **Where to look first (Pareto)** — from `bottlenecks`: top skills / plugins /
   agents / session-kinds by tokens. This is the attribution view the original
   skill lacks.
3. **Ranked opportunities** — from `opportunity_ranking`: for each entry show
   severity badge (🔴 critical / 🟡 warning / 🟢 suggestion), evidence bullets
   with numbers, tokens at stake, and the fix. Note that entries may overlap —
   do not sum them.
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
- Never writes the report or any output file — chat output only.
- No network calls except the optional `ccusage` baseline (may write npm cache).
