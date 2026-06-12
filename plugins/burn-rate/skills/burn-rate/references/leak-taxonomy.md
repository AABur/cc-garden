# Leak taxonomy (Phase 1)

| id | what it catches | source |
|---|---|---|
| model_selection:opus_on_interactive_simple | Opus on short interactive turns (excl. fan-out) | adapted from token-audit |
| context:rot_zone | turns past ~400k context | Thariq Shihipar, Anthropic |
| cache:low_hit_ratio | cache churn, cacheable-minimum aware | adapted from token-audit |
| claude_md:bloat | CLAUDE.md over ~2k tokens | Anthropic cost doc (cited) |

Phase 2 adds: hook_bloat, skill_descriptions, bash_antipatterns, file_reads,
recurring_scripts, tool_schema. Phase 3 adds: subagent_fanout, effort_audit,
error_retries, cache_invalidators.
