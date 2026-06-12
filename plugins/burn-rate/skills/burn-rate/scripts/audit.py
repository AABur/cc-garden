# audit.py
"""burn-rate orchestrator. Local-only token-spend audit -> JSON on stdout.

Runs ccusage for the spend baseline, parses deduped transcripts, inventories config,
computes attribution Pareto, and runs the leak detectors. The SKILL.md body narrates
the JSON in the user's language. burn-rate itself writes nothing; the optional ccusage call may create npm cache entries.
"""
from __future__ import annotations
import argparse
import importlib
import json
from dataclasses import asdict, is_dataclass

import ccusage
import config_inspector
import jsonl_parser
import pricing
import attribution
from detectors import DETECTOR_MODULES

# Resolve detector modules at import time so tests can patch audit._DETECTOR_MODULES.
_DETECTOR_MODULES = [importlib.import_module(mod) for mod in DETECTOR_MODULES]


def run_audit(days: int = 7, skip_ccusage: bool = False, ccusage_timeout: int = 25) -> dict:
    if skip_ccusage:
        ccusage_data, ccusage_error = None, "skipped"
    else:
        ccusage_data, ccusage_error = ccusage.run_daily(days=days, timeout=ccusage_timeout)
    sessions, causal_events, parse_stats, parser_errors = jsonl_parser.parse_all(since_days=days)
    config = config_inspector.build_snapshot()

    leaks, detector_errors = [], []
    for mod in _DETECTOR_MODULES:
        try:
            leaks.extend(mod.detect(sessions, causal_events, config, pricing))
        except Exception as e:
            detector_errors.append(f"{mod.__name__}: {type(e).__name__}: {e}")
    leaks.sort(key=lambda leak: leak.est_weekly_savings_usd, reverse=True)

    bottlenecks = {
        "by_skill": attribution.top_n(attribution.by_dimension(sessions, "attribution_skill")),
        "by_plugin": attribution.top_n(attribution.by_dimension(sessions, "attribution_plugin")),
        "by_agent": attribution.top_n(attribution.by_dimension(sessions, "attribution_agent")),
        "by_session_kind": attribution.top_n(attribution.by_dimension(sessions, "session_kind")),
    }

    model_mix: dict = {}
    for s in sessions:
        for m, c in s.models_used.items():
            model_mix[m] = model_mix.get(m, 0) + c

    accounting_basis = {
        "primary": "local_deduped_transcript_usage",
        "raw_assistant_records": parse_stats.raw_assistant_records,
        "deduped_assistant_requests": parse_stats.deduped_assistant_requests,
        "duplicates_removed": parse_stats.duplicates_removed,
        "sidechain_records": parse_stats.sidechain_assistant_records,
        "user_tool_events": parse_stats.user_tool_events,
        "hook_events": parse_stats.hook_events,
        "total_parsed_events": parse_stats.total_parsed_events,
        "note": (
            "Spend calculations use deduplicated assistant usage records. "
            "Workflow diagnostics use the event stream."
        ),
    }

    reconciliation_status = "skipped" if skip_ccusage else ("failed" if ccusage_error else "matched")
    reconciliation = {
        "status": reconciliation_status,
        "note": "ccusage is an external baseline only, not required for local analysis",
    }

    return {
        "summary": {
            "window_days": days,
            "session_count": len(sessions),
            "turn_count": sum(s.deduped_turn_count for s in sessions),
            "model_mix": model_mix,
            "tool_search_enabled": config.tool_search_enabled,
            "tool_search_mode": config.tool_search_mode,
            "hooks": len(config.hooks),
            "skills_installed": config.skill_count,
            "mcp_servers": len(config.mcp_servers),
            "plugins": len(config.plugins),
        },
        "ccusage": ccusage_data,
        "ccusage_error": ccusage_error,
        "reconciliation": reconciliation,
        "accounting_basis": accounting_basis,
        "parser_errors": parser_errors,
        "detector_errors": detector_errors,
        "bottlenecks": bottlenecks,
        "leaks": [asdict(leak) if is_dataclass(leak) else leak for leak in leaks],
        "opportunity_ranking": sorted(
            [
                {
                    "id": leak.id,
                    "rank_signal_tokens": leak.est_weekly_tokens,
                    "rank_signal_cost_usd": leak.est_weekly_cost_usd,
                    "additive": leak.additive,
                    "overlap_group": leak.overlap_group,
                }
                for leak in leaks
            ],
            key=lambda x: x["rank_signal_cost_usd"],
            reverse=True,
        ),
        "total_savings": {
            "status": "not_reported",
            "reason": "detector scopes overlap; summing them would overstate recoverable spend",
        },
        "pricing_snapshot_date": pricing.SNAPSHOT_DATE,
    }


def main():
    ap = argparse.ArgumentParser(description="Audit Claude Code token usage (read-only).")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--skip-ccusage", action="store_true",
                    help="Skip the ccusage baseline entirely (faster, offline-safe).")
    ap.add_argument("--ccusage-timeout", type=int, default=25,
                    help="Seconds to wait for ccusage before giving up (default: 25).")
    args = ap.parse_args()
    print(json.dumps(
        run_audit(days=args.days, skip_ccusage=args.skip_ccusage, ccusage_timeout=args.ccusage_timeout),
        indent=2, default=str,
    ))


if __name__ == "__main__":
    main()
