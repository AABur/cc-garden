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

## What it checks (Phase 1)

- Opus on interactive simple turns (excludes workflow/subagent fan-out)
- Context-rot zone (>400k-token turns)
- Low cache-hit ratio (cacheable-minimum aware)
- Oversized CLAUDE.md
- Attribution Pareto: tokens by skill / plugin / agent / session-kind

## Privacy

All analysis is local. Payload content is inspected to extract names and sizes but is never persisted or emitted.
The only network call is the optional `ccusage` baseline.

## Credits

Concept and leak taxonomy adapted from
[token-audit](https://github.com/BayramAnnakov/token-audit-skill) by Bayram
Annakov. The implementation here is original. MIT — see [LICENSE](./LICENSE) for
both copyright lines.
