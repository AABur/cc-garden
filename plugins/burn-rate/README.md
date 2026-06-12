# burn-rate

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Read-only](https://img.shields.io/badge/mode-read--only-blue.svg)](#)

Read-only audit of Claude Code token spend: deduplicated transcript analysis,
skill/plugin/MCP/agent attribution, current 2026 pricing, a `ccusage` baseline,
and ranked leaks with concrete fixes. **No configuration is ever modified and burn-rate writes no output files.**
(The optional `ccusage` baseline is fetched via `npx` and may create npm cache entries.)

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

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--days N` | 7 | Look-back window in days |
| `--skip-ccusage` | off | Skip the `ccusage` baseline entirely |
| `--ccusage-timeout N` | 25 | Seconds to wait for `npx ccusage` before aborting |

## What it checks (Phase 1 + Phase 2)

### Spend detectors

| id | what it catches |
|---|---|
| `model_routing:interactive_opus_simple` | Opus on short interactive turns (excludes workflow/subagent fan-out) |
| `model_routing:subagent_opus_simple` | Opus on short background/subagent turns |
| `context:rot_zone` | Turns past ~400k context |
| `cache:low_hit_ratio` | Cache churn, cacheable-minimum aware |
| `claude_md:bloat` | CLAUDE.md over ~2k tokens |

### Causal detectors (Phase 2)

| id | what it catches |
|---|---|
| `causal:hook_output_bloat` | Hook stdout feeding oversized text into context |
| `causal:bash_antipatterns` | Shell commands known to inflate output (cat large files, find /, etc.) |
| `causal:repeated_reads` | Same file read 4+ times in a session with large content |

### Workload detectors (Phase 2)

| id | what it catches |
|---|---|
| `workload:high_volume_parallel_workload` | Projects with high parallel session volume (>10 sessions/day) |
| `workload:possible_recurring_automation` | Multi-signal: high volume + short sessions + no tool-search + many hooks |

## Output schema

Key top-level fields:

| Field | Description |
|---|---|
| `accounting_basis` | Local deduplication stats: raw vs deduped records, sidechain count, event totals |
| `opportunity_ranking` | Ranked list of findings by `rank_signal_cost_usd` (descending). **Not additive** — entries may overlap. |
| `total_savings` | Always `status: "not_reported"` because ranking scopes overlap |
| `reconciliation` | `ccusage` comparison status: `matched`, `skipped`, or `failed` |
| `leaks` | Individual findings, each with a `basis` field (`spend`, `causal`, `workload`, or `mixed`) |
| `bottlenecks` | Top consumers by skill / plugin / agent / session-kind |

> Primary cost basis is local deduplicated assistant usage. Causal and workload
> events are parsed for attribution and workflow diagnosis only; their estimates
> are not additive spend.

## Attribution Pareto

`bottlenecks` ranks token consumers by skill, plugin, agent, and session-kind.
This is the attribution view the original token-audit concept does not provide.

## Privacy

All analysis is local. Payload content is inspected to extract names and sizes but is never persisted or emitted.
The only network call is the optional `ccusage` baseline.

## Credits

Concept and leak taxonomy adapted from
[token-audit](https://github.com/BayramAnnakov/token-audit-skill) by Bayram
Annakov. The implementation here is original. MIT — see [LICENSE](./LICENSE) for
both copyright lines.
