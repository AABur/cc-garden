"""Stream-based trigger eval that exits early on first Skill match.

Logic:
- For each query, spawn `claude -p ... --output-format stream-json` and read
  its stdout line-by-line.
- Track every assistant tool_use event. As soon as we see a `Skill` tool_use
  whose `skill` input contains the target skill name → return triggered=True
  and kill the subprocess. We don't need to wait for the whole skill workflow.
- If the stream ends naturally without that → triggered=False.
- If the timeout expires → triggered=False, mark `note: "timeout"`.

This avoids the bug in skill-creator's run_eval (which returns False as soon
as Claude makes any non-Skill tool call). It also runs much faster for
should-trigger cases — typically 5-15s instead of full skill execution.
"""

from __future__ import annotations

import argparse
import json
import os
import select
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def run_query(query: str, skill_name: str, timeout: int = 180) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = [
        "claude", "-p", query,
        "--output-format", "stream-json",
        "--verbose",
        "--include-partial-messages",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    triggered = False
    skill_calls: list[str] = []
    other_tools: list[str] = []
    note = ""
    start = time.time()
    buffer = ""

    try:
        while time.time() - start < timeout:
            if proc.poll() is not None:
                rest = proc.stdout.read()
                if rest:
                    buffer += rest.decode("utf-8", errors="replace")
                break
            ready, _, _ = select.select([proc.stdout], [], [], 1.0)
            if not ready:
                continue
            chunk = os.read(proc.stdout.fileno(), 8192)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") != "assistant":
                    continue
                msg = ev.get("message", {})
                for c in msg.get("content", []):
                    if c.get("type") != "tool_use":
                        continue
                    name = c.get("name", "")
                    inp = c.get("input", {})
                    if name == "Skill":
                        slug = (inp.get("skill") or "").strip()
                        skill_calls.append(slug)
                        if skill_name in slug:
                            triggered = True
                    else:
                        other_tools.append(name)
                if triggered:
                    break
            if triggered:
                break
        else:
            note = "timeout"
    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    return {
        "triggered": triggered,
        "skill_calls": skill_calls,
        "other_tools_count": len(other_tools),
        "exit_code": proc.returncode,
        "elapsed_s": round(time.time() - start, 1),
        "note": note,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--eval-set", required=True)
    p.add_argument("--skill-name", default="retro")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--output", default="-")
    args = p.parse_args(argv)

    items = json.loads(Path(args.eval_set).read_text())

    def worker(item):
        try:
            return item, run_query(item["query"], args.skill_name, args.timeout)
        except Exception as e:
            return item, {
                "triggered": False,
                "skill_calls": [],
                "other_tools_count": 0,
                "exit_code": -1,
                "elapsed_s": 0,
                "note": f"error: {type(e).__name__}: {e}",
            }

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(worker, it) for it in items]
        for fut in as_completed(futures):
            item, res = fut.result()
            verdict = res["triggered"] == item["should_trigger"]
            mark = "PASS" if verdict else "FAIL"
            sign = "+" if item["should_trigger"] else "−"
            print(
                f"[{mark}] [{sign}] {res['elapsed_s']:>5}s "
                f"got={res['triggered']} skills={res['skill_calls']!r} "
                f"-- {item['query'][:80]}…",
                file=sys.stderr,
                flush=True,
            )
            results.append({
                "query": item["query"],
                "should_trigger": item["should_trigger"],
                "triggered": res["triggered"],
                "pass": verdict,
                "skill_calls": res["skill_calls"],
                "other_tools_count": res["other_tools_count"],
                "elapsed_s": res["elapsed_s"],
                "exit_code": res["exit_code"],
                "note": res["note"],
            })
            if args.output != "-":
                Path(args.output).write_text(
                    json.dumps({"in_progress": True, "results": results}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

    passed = sum(1 for r in results if r["pass"])
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "positives": {
            "total": sum(1 for r in results if r["should_trigger"]),
            "passed": sum(1 for r in results if r["should_trigger"] and r["pass"]),
        },
        "negatives": {
            "total": sum(1 for r in results if not r["should_trigger"]),
            "passed": sum(1 for r in results if not r["should_trigger"] and r["pass"]),
        },
    }
    payload = {"summary": summary, "results": results}
    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output == "-":
        print(out)
    else:
        Path(args.output).write_text(out, encoding="utf-8")
    print(
        f"\nResults: {passed}/{len(results)} passed "
        f"(positives {summary['positives']['passed']}/{summary['positives']['total']}, "
        f"negatives {summary['negatives']['passed']}/{summary['negatives']['total']})",
        file=sys.stderr,
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
