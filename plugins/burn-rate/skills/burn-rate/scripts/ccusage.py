# ccusage.py
"""Thin wrapper around the ccusage CLI for the spend baseline.

Runs in online `auto` mode (fresh LiteLLM prices + dedup). Best-effort: if Node
or ccusage is missing, returns (None, error) and the audit proceeds without it.
"""
from __future__ import annotations
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

_CCUSAGE_VERSION = os.environ.get("CCUSAGE_VERSION", "20.0.11")


def _run(args: list, timeout: int = 180) -> tuple:
    try:
        proc = subprocess.run(["npx", "-y", f"ccusage@{_CCUSAGE_VERSION}", *args],
                              capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "npx/node not found"
    except subprocess.TimeoutExpired:
        return 124, "", "ccusage timed out"


def run_daily(days: int = 7) -> tuple:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y%m%d")
    until = now.strftime("%Y%m%d")
    rc, out, err = _run(["daily", f"--since={since}", f"--until={until}", "--json"])
    if rc != 0:
        return None, f"ccusage unavailable: {(err or 'failed').strip()}"
    try:
        return json.loads(out), None
    except json.JSONDecodeError as e:
        return None, f"ccusage JSON parse failed: {e}"
