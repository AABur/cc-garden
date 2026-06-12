# burn-rate Phase 3 Plan — Hook Tax, Workload Cadence, Config Tax

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three real diagnostic gaps surfaced by comparing burn-rate against
`token-audit`, **without** inheriting token-audit's three methodological flaws
(undeduplicated counts, additive savings totals, and the false-positive "runaway" label).

**Origin:** Critical review of token-audit's parallel run (2026-06-12). token-audit's
*numbers* were inflated ~3-5× by counting raw/undeduplicated records and were presented
additively; its "possible runaway script" label is exactly the false positive Phase 2
removed. But token-audit surfaced three genuine blind spots in burn-rate that this phase
closes.

**Primary principles (carry forward from Phase 2 — do not regress):**

1. **Deduplicated basis.** All spend math stays on deduplicated assistant usage. Never
   chase token-audit's larger numbers; they are an artifact of weaker accounting.
2. **Non-additive.** New detectors emit `additive: false` with an `overlap_group`. Never
   sum across detectors into a single savings figure.
3. **Show data, not scary labels.** Where Phase 2 classifies (e.g. workload), surface the
   *underlying signals* (cadence, off-hours, sidechain share) as evidence so the user
   judges "legitimate batch vs runaway" — do not hide the data behind a quiet label, and
   do not assert "runaway" on volume alone.
4. **Conservative wording.** Diagnostics are hints with confidence and impact, not verdicts.

---

## Task 1: Make hooks a first-class cost (burn-rate is currently blind)

**Problem:** burn-rate parses `assistant` + `user` records only. Hook injections — which
land on **every** SessionStart / UserPromptSubmit turn — are never parsed. The existing
`detectors/hook_output_bloat.py` is **misnamed**: it sums `tool_result` content, not hook
output. `CausalEvent.hook_name`/`hook_event` and `ParseStats.hook_events` are declared but
never populated (`hook_events == 0` always). token-audit caught a SessionStart hook firing
102× at ~1,445 tokens each (the remember/handoff hook injecting full `today-*.md`); burn-rate
cannot see it.

**Verified JSONL shape (from live transcripts, Claude Code 2.1.173):**

Hook injections are `type: "attachment"` records:
```json
{
  "type": "attachment",
  "isSidechain": false,
  "sessionId": "...",
  "timestamp": "...",
  "attachment": {
    "type": "hook_success",            // also hook_error / hook_blocked
    "hookName": "SessionStart:clear",
    "hookEvent": "SessionStart",
    "toolUseID": "...",
    "content": "=== HANDOFF ===\n...",  // the injected text — this is the cost
    "stdout": "...",
    "stderr": "",
    "exitCode": 0,
    "command": "bash ...",
    "durationMs": 49
  }
}
```

There is also a `type: "system", subtype: "stop_hook_summary"` record carrying
`hookCount`, `hookInfos[].command`, `hookInfos[].durationMs`, `hasOutput` — useful for
counting Stop-hook fires even when they produce no output.

**Required behavior:**

- [ ] Parse `attachment` records whose `attachment.type` starts with `hook_`. Emit a
      `CausalEvent` with `event_type="hook"`, `hook_name`, `hook_event`,
      `content_size = len(attachment.content or attachment.stdout)`, `is_error` from
      `hook_error`/non-zero `exitCode`, and `session_id`/`is_sidechain`. Never store the
      full command or content — size + name only (privacy parity with `command_head`).
- [ ] Populate `ParseStats.hook_events` with the real count.
- [ ] Rename the current `hook_output_bloat` detector to `tool_output_bloat`
      (id `causal:tool_output_bloat`) — it measures `tool_result`, and the name should say so.
      Update its tests.
- [ ] Add `detectors/hook_injection_bloat.py` (id `causal:hook_injection_bloat`,
      basis `causal`, `overlap_group="hook_tax"`, `additive=false`). Group hook events by
      `hook_name` + `hook_event`. For each hook: fires, total injected chars, avg chars/fire,
      est tokens (`chars // 4`). Weight SessionStart / UserPromptSubmit hooks by the
      per-turn multiplier (they inject on every qualifying turn), and report the worst hook
      by total injected tokens/week.
- [ ] Wording: name the specific hook, note that per-turn hooks pay on every turn, and
      suggest injecting *pointers* (paths) rather than full file contents where applicable.

---

## Task 2: Surface workload cadence as evidence (judge, don't hide)

**Problem:** `workload_classifier` computes 5 automation signals but only emits a quiet
`high_volume_parallel_workload` label. The *cadence data the user needs to decide* "batch
vs runaway" (modal interval, off-hours concentration, interactive share) is computed and
then discarded. token-audit's "~100s modal interval" was genuinely useful diagnostic data
burn-rate hides.

**Required behavior:**

- [ ] For every `high_volume_parallel_workload` finding, add the underlying signals to
      `evidence`: sessions/day, **modal inter-session interval** and its stability
      (coefficient of variation), **off-hours %** (share outside 08:00-22:00 local),
      interactive share, sidechain share, top sessions by tokens.
- [ ] Keep the strict 5-signal gate for the `possible_recurring_automation` label, but the
      cadence evidence must appear **regardless** of whether the automation label fires — so
      the user can override the classification with the data in front of them.
- [ ] Wording rule: "High-volume parallel workload. Cadence: modal interval ~N s
      (CV X%), off-hours Y%. This is consistent with active batch work; it is **not**
      flagged as scheduled automation because [which signals are absent]. If this is a cron
      / `claude -p` loop you forgot about, the cadence above is where to look."

---

## Task 3: Skill / plugin description context tax (verified real)

**Problem:** burn-rate inventories `skill_count` but never measures the token cost of
installed skill/plugin **descriptions**. Verified via Claude Code docs (2026-06-12): skill
descriptions load into context at session start on **every** turn, and `ENABLE_TOOL_SEARCH`
defers **MCP tools only — not skills**. So N installed skills impose a real per-turn tax
that tool-search does not reduce. The user's environment shows 86 skills / 26 plugins.

**Required behavior:**

- [ ] In `config_inspector`, sum the approx tokens of each installed skill's frontmatter
      `description` (and plugin `description` from `plugin.json`). Expose as
      `skill_description_tokens` / `plugin_description_tokens` plus counts.
- [ ] Add `detectors/config_description_tax.py` (id `config:skill_description_tax`,
      basis `mixed`, `overlap_group="config_tax"`, `additive=false`).
      `est_weekly_tokens = total_description_tokens × deduped_turns` (descriptions ride
      every turn, like CLAUDE.md). Only flag above a threshold.
- [ ] Evidence: total skills/plugins, total description tokens, per-turn cost, top plugins
      by description weight. Mitigation: `skillOverrides` / `disable-model-invocation: true`
      in settings.json for rarely-used skills; uninstalling unused plugins.
- [ ] Wording must state explicitly that **tool-search does NOT defer skill descriptions**
      (a common misconception), so the fix is pruning / overrides, not enabling tool-search.

---

## Task 4: Enrich existing causal/cache detectors with the detail token-audit had

**Problem:** burn-rate's `bash_antipatterns` reports a flat count ("56 shell calls");
token-audit's per-command breakdown (grep 160× / find 122× / cat 53× …) is more actionable.
The cache detector measures hit ratio but omits the "pause > 5 min kills the cache → full
prefix rewrite" mechanism and peak-day concentration.

**Required behavior:**

- [ ] `bash_antipatterns` evidence: per-command counts (grep / find / cat / head / tail /
      sed / awk), each mapped to its native Claude Code equivalent (Grep / Glob / Read / Edit).
      Keep severity `suggestion`; keep suppression of low-impact findings.
- [ ] `cache` detector: add a cache-discipline signal. Detect sessions where a > 5-minute
      gap between turns precedes a large cache-write (prefix rewrite). Surface peak-day token
      concentration (top 1-2 days by tokens) as context. Keep it a `warning`, basis `spend`.
- [ ] Both stay `additive: false` within their existing `overlap_group`s.

---

## Task 5: Suggested action for legitimate high-volume workloads (not a leak)

**Problem:** When a high-volume workload is legitimate batch (e.g. video-data extraction),
the right move may be routing it to a local model — but that is an *option*, not a leak.

**Required behavior:**

- [ ] For `high_volume_parallel_workload`, add an optional `suggested_action` (not a savings
      claim): "If this is an unattended batch, consider routing it to a local model
      (e.g. Ollama) so it does not consume subscription headroom; validate output quality on
      a parallel run first." Make clear this is a routing suggestion, not a detected leak,
      and emits no token/cost savings figure.

---

## Implementation Order

- [ ] Step 1: Parse hook `attachment` records; populate `hook_events`, `CausalEvent` hook fields.
- [ ] Step 2: Rename `hook_output_bloat` → `tool_output_bloat`; add `hook_injection_bloat`.
- [ ] Step 3: Add cadence evidence to `workload_classifier`.
- [ ] Step 4: Add `config_inspector` description-token measurement + `config_description_tax`.
- [ ] Step 5: Enrich `bash_antipatterns` (per-command) and `cache` (discipline / peak day).
- [ ] Step 6: Add `suggested_action` to high-volume workload findings.
- [ ] Step 7: Update SKILL.md, README, leak-taxonomy, and tests.

---

## Acceptance Criteria

- [ ] Hook injections are parsed; `accounting_basis.hook_events > 0` when hooks fired, and a
      per-hook injection-tax finding names the worst hook (e.g. the SessionStart memory hook).
- [ ] The `tool_result` detector is no longer mislabeled "hook"; a distinct true-hook detector exists.
- [ ] `high_volume_parallel_workload` evidence shows modal interval, off-hours %, and
      sidechain share, so the user can judge batch-vs-automation from the data — without the
      word "runaway" appearing on volume alone.
- [ ] Skill/plugin description tax is measured against deduplicated turns and flagged only
      above a threshold, with the explicit note that tool-search does not defer skills.
- [ ] `bash_antipatterns` shows per-command counts; cache detector surfaces the >5-min-pause
      prefix-rewrite signal.
- [ ] No detector contributes to a summed savings total; all new findings are
      `additive: false` with an `overlap_group`.
- [ ] All numbers remain on the deduplicated basis; no inflation toward token-audit's counts.
- [ ] Tests cover hook parsing, the rename, cadence evidence, the description-tax detector,
      and the enriched bash/cache evidence. Full suite stays green.
