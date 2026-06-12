# burn-rate Next Iteration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `burn-rate` from a Phase 1 model/context auditor into a stricter local token-audit system that identifies large cost surfaces, separates legitimate high-volume workloads from leaks, and avoids overstating additive savings.

**Primary principle:** `token-audit` is a comparison benchmark, not the source of truth. `burn-rate` should use its own accounting model and report where the largest cost surfaces are, with conservative wording when signals are diagnostic rather than conclusive.

**Architecture direction:** Keep local-only analysis. Use deduplicated assistant usage as the primary spend basis. Add causal and workload event parsing for attribution, but do not add those event estimates into billed usage without reconciliation.

---

## Accounting Model

`burn-rate` must use three separate ledgers:

1. **Spend ledger**
   - Primary basis for cost and token pressure.
   - Source: deduplicated assistant usage records.
   - Fields: model, input tokens, output tokens, cache read, cache write 5m/1h, session, project, sidechain flag, session kind, attribution fields.
   - Purpose: answer "where is the large cost surface?"

2. **Causal ledger**
   - Diagnostic basis, not additive spend.
   - Source: user/tool/hook/event records.
   - Fields: Bash command head, Read/Edit/Write file path, tool result size, hook name/event/output size, tool use id.
   - Purpose: explain why spend may be happening.

3. **Workload ledger**
   - Classification basis.
   - Source: spend + causal ledgers.
   - Categories: interactive, subagent/sidechain, background, high-volume parallel workload, possible recurring automation.
   - Purpose: separate legitimate active workloads from likely leaks.

Report rule:

> Primary cost basis is local deduplicated assistant usage. Tool, hook, and user events are parsed for attribution and workflow diagnosis only; their estimates are not additive spend unless explicitly reconciled.

---

## Task 1: Replace "runaway" with high-volume workload classification

**Problem:** A high session rate can be legitimate parallel work. For example, active video-data extraction experiments may create many sessions and subagents without any cron, launchd, GitHub Actions schedule, or `claude -p` loop.

**Required behavior:**

- [ ] Add a workload classifier for high-volume project activity.
- [ ] Name the primary signal neutrally, for example `parallel_workload_burst` or `high_volume_parallel_workload`.
- [ ] Do not call a project "runaway" based only on sessions/day or modal interval.
- [ ] Emit "possible recurring automation" only when multiple strong signals align:
  - stable repeated interval,
  - repeated prompt/tool pattern,
  - repeated cwd and command pattern,
  - off-hours concentration,
  - little or no surrounding interactive activity.
- [ ] For high-volume but expected work, report model mix, token buckets, cache profile, sidechain/subagent share, and top sessions.

Expected wording:

```text
kards-llm-recognition is a high-volume parallel workload: many sessions and substantial token load. No conclusive evidence of scheduled runaway automation was found. Treat this as active workload unless repeated cadence and repeated prompt/tool evidence appear.
```

---

## Task 2: Add tool and hook diagnostics

**Problem:** Phase 1 parses assistant turns only. It cannot see enough detail to diagnose Bash usage, repeated reads, tool result sizes, or hook output tax.

**Parser requirements:**

- [ ] Parse `assistant`, `user`, and `attachment` records.
- [ ] Store privacy-safe summaries only.
- [ ] For Bash tool calls, store `command_head`, not the full command.
- [ ] For Read/Edit/Write, store `file_path`.
- [ ] For tool results, store `tool_use_id`, `is_error`, and content size only.
- [ ] For hooks, store `hook_name`, `hook_event`, and output size only.
- [ ] Preserve existing deduplicated assistant usage behavior for the spend ledger.

**Detector requirements:**

- [ ] Add `hook_output_bloat` with high confidence when hook output is large enough to matter.
- [ ] Add `bash_antipatterns` as Claude Code workflow hygiene, not as an absolute error.
- [ ] Add `repeated_reads` as a low-to-medium confidence hint.
- [ ] Rank diagnostics by estimated token impact and share of overall spend surface.
- [ ] Suppress low-impact diagnostics from "fix first" recommendations.

Wording rule:

```text
Shell reads/searches detected. In Claude Code this can be costlier than native tools, but some calls may be intentional. Estimated impact is small; treat as workflow hygiene, not primary savings.
```

---

## Task 3: Make subagent and fan-out cost first-class

**Problem:** Phase 1 excludes sidechain and background turns from the simple Opus detector. This avoids mixing categories, but it also hides expensive subagent/fan-out behavior from actionable leak analysis.

**Required behavior:**

- [ ] Keep `interactive_opus_simple` separate.
- [ ] Add `subagent_opus_simple` for short Opus turns inside sidechain/subagent work.
- [ ] Add `parallel_fanout_load` as a workload category, not a leak by default.
- [ ] Add `background_load` as a workload category, not a leak by default.
- [ ] Attribute fan-out by project, agent, model, token bucket, and cache behavior.
- [ ] Recommend model routing inside fan-out only when evidence supports it.

Do not simply include sidechain turns in the existing interactive detector.

Expected wording:

```text
Subagent/fan-out load: N tokens/week across workflow-subagent. This appears to be active parallel workload, not automatically a leak. M short Opus worker turns could likely run on Sonnet; estimated model-routing opportunity: X tokens/week.
```

---

## Task 4: Expose accounting basis without chasing external turn counts

**Problem:** Different tools count different things. Raw event counts, assistant records, deduplicated requests, tool results, hooks, and sidechain records are not interchangeable.

**Required behavior:**

- [ ] Keep deduplicated assistant usage as the primary spend basis.
- [ ] Add summary counters for transparency:
  - raw assistant records,
  - deduplicated assistant requests,
  - duplicates removed,
  - sidechain assistant records,
  - user/tool result events,
  - hook events,
  - total parsed event records.
- [ ] Label each detector with its basis:
  - `spend`,
  - `causal`,
  - `workload`,
  - `mixed`.
- [ ] Do not frame these counters as reconciliation with `token-audit`.
- [ ] Frame them as the internal accounting model.

Expected report language:

```text
Spend calculations use deduplicated assistant usage records. Workflow diagnostics use the event stream because tool results, hooks, and repeated reads live outside assistant usage records.
```

---

## Task 5: Make ccusage non-blocking and secondary

**Problem:** The optional `ccusage` baseline can block the audit through `npx` and network/DNS failures. It is useful for reconciliation, but it should not be the first or mandatory source of the local report.

**Required behavior:**

- [ ] Add `--skip-ccusage`.
- [ ] Add `--ccusage-timeout`, defaulting to 20-30 seconds.
- [ ] Run local transcript parsing and detectors independently of ccusage.
- [ ] Treat ccusage as external baseline/reconciliation.
- [ ] Prefer an installed `ccusage` binary if available before using `npx`.
- [ ] Include `ccusage_error` without failing the local audit.
- [ ] Update SKILL.md so spend summary starts from local transcript usage, then ccusage baseline if available.

Suggested JSON:

```json
{
  "primary_basis": "local_deduped_transcript_usage",
  "ccusage": null,
  "ccusage_error": "...",
  "reconciliation": {
    "status": "skipped|failed|matched|diverged",
    "note": "ccusage is an external baseline only, not required for local analysis"
  }
}
```

---

## Task 6: Stop reporting additive total savings

**Problem:** Detector estimates overlap. Summing them overstates recoverable spend. A short Opus turn can also be part of subagent fan-out, high-volume workload, CLAUDE.md prompt tax, and tool workflow diagnostics.

**Required behavior:**

- [ ] Remove or de-emphasize `total_weekly_savings_usd`.
- [ ] Replace it with opportunity ranking.
- [ ] Add `overlap_group` or `basis_scope` to each detector.
- [ ] Add `additive: false` by default.
- [ ] Use local spend ledger or ccusage baseline as the upper bound.
- [ ] Report detector estimates as ranking signals, not invoices or additive savings.

Suggested JSON:

```json
{
  "opportunity_ranking": [
    {
      "id": "model_routing:interactive_opus_simple",
      "rank_signal_tokens": 84141799,
      "rank_signal_cost_usd": 35.48,
      "additive": false,
      "overlap_group": "model_routing"
    }
  ],
  "total_savings": {
    "status": "not_reported",
    "reason": "detector scopes overlap; summing them would overstate recoverable spend"
  }
}
```

Expected wording:

```text
Largest optimization surface: model routing in short Opus turns, about N tokens affected. Opportunity estimates are ranking signals, not additive savings.
```

---

## Implementation Order

- [ ] Step 1: Add accounting-basis fields and summary counters.
- [ ] Step 2: Add `--skip-ccusage` and `--ccusage-timeout`.
- [ ] Step 3: Extend parser with causal event summaries.
- [ ] Step 4: Add tool and hook diagnostics.
- [ ] Step 5: Add workload classifier and high-volume parallel workload detector.
- [ ] Step 6: Split interactive and subagent model-routing opportunities.
- [ ] Step 7: Replace additive savings totals with opportunity ranking.
- [ ] Step 8: Update SKILL.md, README, and tests.

---

## Acceptance Criteria

- [ ] The report identifies large cost surfaces primarily by deduplicated assistant usage tokens.
- [ ] The report does not call legitimate high-volume parallel work "runaway" without strong evidence.
- [ ] `kards-llm-recognition`-style active parallel work is classified as high-volume workload by default.
- [ ] Subagent/fan-out cost is visible and actionable without being treated as waste by default.
- [ ] Bash, repeated reads, and hooks are shown as diagnostics with confidence and impact, not blanket errors.
- [ ] `ccusage` failure does not delay or block the local audit beyond the configured timeout.
- [ ] Detector estimates are not summed into a fake total savings figure.
- [ ] Tests cover parser accounting counters, workload classification, non-additive opportunity ranking, and ccusage skip/timeout behavior.

