# detectors/__init__.py
"""Leak dataclass + detector registry. Each detector module exposes
`detect(sessions, causal_events, config, pricing_mod) -> list[Leak]`."""
from __future__ import annotations
from dataclasses import dataclass, field

DETECTOR_MODULES = [
    "detectors.model_selection",
    "detectors.context_rot",
    "detectors.cache",
    "detectors.claude_md_bloat",
]

SEVERITIES = ("critical", "warning", "suggestion")


@dataclass
class Leak:
    id: str
    title: str
    severity: str
    category: str
    basis: str = "spend"       # "spend", "causal", "workload", "mixed"
    additive: bool = False
    overlap_group: str = ""
    evidence: list = field(default_factory=list)
    est_weekly_tokens: int = 0
    est_weekly_cost_usd: float = 0.0
    est_weekly_savings_usd: float = 0.0
    fix_action: str = ""

    def __post_init__(self):
        # Enforce the severity contract at construction so a typo in a detector
        # surfaces immediately instead of silently mis-sorting/filtering downstream.
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}, got {self.severity!r}")
