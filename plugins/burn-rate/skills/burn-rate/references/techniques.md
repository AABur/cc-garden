# Token-engineering levers (2026)

Prompt caching (5m=1.25x / 1h=2x write, read ~0.1x; per-model cacheable minimum),
context editing / proactive `/compact` (context rot past ~400k), per-subagent
model selection, tool-search vs full MCP schema loading, `effort` parameter
(Sonnet 4.6 defaults to high), subagent fan-out multiplier, `.claudeignore`,
plan-mode, `@file` vs pasted blobs. See spec for sourcing.
