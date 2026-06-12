# ccusage.py
"""Thin wrapper around the ccusage CLI for the spend baseline.

Runs in online `auto` mode (fresh LiteLLM prices + dedup). Best-effort: if Node
or ccusage is missing, returns (None, error) and the audit proceeds without it.

Binary detection: if `ccusage` is on PATH it is called directly; otherwise
falls back to `npx -y ccusage@<version>` so Node-only installs still work.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

_CCUSAGE_VERSION = os.environ.get("CCUSAGE_VERSION", "20.0.11")


def _run(args: list, timeout: int = 25) -> tuple:
    binary = shutil.which("ccusage")
    if binary:
        cmd = [binary, *args]
    else:
        cmd = ["npx", "-y", f"ccusage@{_CCUSAGE_VERSION}", *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "npx/node not found"
    except subprocess.TimeoutExpired:
        return 124, "", "ccusage timed out"


def run_daily(days: int = 7, timeout: int = 25) -> tuple:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y%m%d")
    until = now.strftime("%Y%m%d")
    rc, out, err = _run(["daily", f"--since={since}", f"--until={until}", "--json"], timeout=timeout)
    if rc != 0:
        return None, f"ccusage unavailable: {(err or 'failed').strip()}"
    try:
        return json.loads(out), None
    except json.JSONDecodeError as e:
        return None, f"ccusage JSON parse failed: {e}"
