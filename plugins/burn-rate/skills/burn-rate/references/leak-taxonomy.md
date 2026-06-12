# Leak taxonomy

## Phase 1 (implemented)

| id | what it catches | source |
|---|---|---|
| `model_routing:interactive_opus_simple` | Opus on short interactive turns (excl. fan-out) | adapted from token-audit |
| `context:rot_zone` | turns past ~400k context | Thariq Shihipar, Anthropic |
| `cache:low_hit_ratio` | cache churn, cacheable-minimum aware | adapted from token-audit |
| `claude_md:bloat` | CLAUDE.md over ~2k tokens | Anthropic cost doc (cited) |

## Phase 2 (implemented)

| id | ledger | what it catches |
|---|---|---|
| `model_routing:subagent_opus_simple` | spend | Opus on short background/subagent turns |
| `causal:tool_output_bloat` | causal | Large tool_result output inflating per-session context |
| `causal:hook_injection_bloat` | causal | Hook-injected content imposing a recurring context tax |
| `causal:bash_antipatterns` | causal | Shell commands known to inflate output |
| `causal:repeated_reads` | causal | Same file read 4+ times in a session with large content |
| `workload:high_volume_parallel_workload` | workload | Projects with high parallel session volume (>10 sessions/day) |
| `workload:possible_recurring_automation` | workload | Multi-signal: high volume + short sessions + no tool-search + many hooks |

## Phase 3 (implemented)

All Phase 3 detectors are `additive: false` (their estimates are ranking/context-tax
signals, not summed into the spend total).

| id | ledger | overlap_group | what it catches |
|---|---|---|---|
| `cache:prefix_rewrite_after_pause` | spend | `cache_efficiency` | A >5-min pause between turns precedes a large cache-write (prefix rewrite); evidence includes peak-day token concentration |
| `config:skill_description_tax` | mixed | `config_tax` | Skill/plugin descriptions load into context every turn (tool-search does not defer them); measures the per-turn description tax |
| `causal:hook_injection_bloat` | causal | `hook_tax` | True hook-injection tax: groups hook events by hook_name + hook_event, observed `chars//4` est tokens, notes per-turn SessionStart/UserPromptSubmit hooks |

### Renamed in Phase 3

`causal:hook_output_bloat` → **`causal:tool_output_bloat`** (overlap_group `tool_output`,
`additive: false`). The detector measures `tool_result` content size; the old name
incorrectly implied hook stdout.

### Enriched in Phase 3

- `causal:bash_antipatterns` (overlap_group `bash_patterns`, `additive: false`) — now a
  per-command breakdown (grep/find/cat/head/tail/sed/awk), each mapped to its native
  Claude Code tool (Grep/Glob/Read/Edit).
- `workload:high_volume_parallel_workload` (overlap_group `workload_classification`,
  `additive: false`) — now emits cadence evidence (modal inter-session interval + CV%,
  off-hours %, interactive share, sidechain share, top sessions) and an optional
  `suggested_action` recommending an unattended batch be routed to a local model
  (e.g. Ollama). The suggestion is explicitly NOT a token/cost savings claim.

Also in Phase 3: `accounting_basis.hook_events` is now populated (previously always 0),
and the `Leak` dataclass gained a `suggested_action: str = ""` field.
