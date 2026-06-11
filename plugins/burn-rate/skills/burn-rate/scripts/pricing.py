# pricing.py
"""2026 price model for Claude Code token usage. Snapshot — see references/pricing-2026.md.

Prices are USD per million tokens. Unknown/non-Claude models cost 0 (we do not
guess), and synthetic turns cost 0. ccusage remains the authority for the spend
baseline; this table only powers per-leak detector estimates.
"""
from __future__ import annotations
from dataclasses import dataclass

# family -> per-million rates + cacheable minimum (tokens)
PRICING = {
    "opus":   {"input": 5.0,  "output": 25.0, "cw5m": 6.25,  "cw1h": 10.0, "cr": 0.5, "min": 4096},
    "sonnet": {"input": 3.0,  "output": 15.0, "cw5m": 3.75,  "cw1h": 6.0,  "cr": 0.3, "min": 2048},
    "haiku":  {"input": 1.0,  "output": 5.0,  "cw5m": 1.25,  "cw1h": 2.0,  "cr": 0.1, "min": 4096},
    "fable":  {"input": 10.0, "output": 50.0, "cw5m": 12.5,  "cw1h": 20.0, "cr": 1.0, "min": 2048},
}
SNAPSHOT_DATE = "2026-06-04"


@dataclass
class TokenBreakdown:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total(self) -> int:
        return (self.input_tokens + self.output_tokens + self.cache_write_5m_tokens
                + self.cache_write_1h_tokens + self.cache_read_tokens)


def resolve_family(model: str | None) -> str | None:
    """Map a model ID to a pricing family. Returns 'synthetic' for synthetic
    turns, None for non-Claude/unknown (which we refuse to price)."""
    if not model:
        return None
    m = model.lower()
    if m == "<synthetic>":
        return "synthetic"
    if m.startswith("claude-opus-4"):
        return "opus"
    if m.startswith("claude-sonnet-4"):
        return "sonnet"
    if m.startswith("claude-haiku-4"):
        return "haiku"
    if m.startswith("claude-fable-5") or m.startswith("claude-mythos-5"):
        return "fable"
    return None


def estimate_cost(b: TokenBreakdown, model: str | None) -> float:
    fam = resolve_family(model)
    if fam in (None, "synthetic"):
        return 0.0
    p = PRICING[fam]
    cost = (b.input_tokens * p["input"] + b.output_tokens * p["output"]
            + b.cache_write_5m_tokens * p["cw5m"] + b.cache_write_1h_tokens * p["cw1h"]
            + b.cache_read_tokens * p["cr"]) / 1_000_000
    return round(cost, 6)


def cacheable_minimum(model: str | None) -> int | None:
    fam = resolve_family(model)
    if fam in (None, "synthetic"):
        return None
    return PRICING[fam]["min"]
