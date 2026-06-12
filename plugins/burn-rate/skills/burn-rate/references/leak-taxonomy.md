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

## Phase 3 (planned)

Phase 3 adds: subagent_fanout, effort_audit, error_retries, cache_invalidators,
tool_schema bloat, skill_description bloat.
