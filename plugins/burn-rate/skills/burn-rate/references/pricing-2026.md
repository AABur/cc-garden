# Pricing snapshot — 2026-06-04

USD per million tokens. Source: Anthropic `claude-api` skill (cached 2026-06-04).
ccusage remains the authority for the spend baseline; this table powers per-leak
detector estimates only.

| family | input | output | cache_write_5m | cache_write_1h | cache_read | cacheable_min |
|---|---|---|---|---|---|---|
| opus (4.x) | 5 | 25 | 6.25 | 10 | 0.5 | 4096 |
| sonnet (4.6) | 3 | 15 | 3.75 | 6 | 0.3 | 2048 |
| haiku (4.5) | 1 | 5 | 1.25 | 2 | 0.1 | 4096 |
| fable-5 | 10 | 50 | 12.5 | 20 | 1.0 | 2048 |

Current 1M-context models carry no long-context premium. Refresh this table when
Anthropic pricing changes; the spend baseline stays current automatically via
ccusage's online price refresh.
