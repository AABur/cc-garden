# detectors/__init__.py
"""Leak dataclass + detector registry. Each detector module exposes
`detect(sessions, config, pricing_mod) -> list[Leak]`."""
from __future__ import annotations
from dataclasses import dataclass, field

DETECTOR_MODULES = [
    "detectors.model_selection",
    "detectors.context_rot",
    "detectors.cache",
    "detectors.claude_md_bloat",
]


@dataclass
class Leak:
    id: str
    title: str
    severity: str            # "critical" | "warning" | "suggestion"
    category: str
    evidence: list = field(default_factory=list)
    est_weekly_tokens: int = 0
    est_weekly_cost_usd: float = 0.0
    est_weekly_savings_usd: float = 0.0
    fix_action: str = ""
