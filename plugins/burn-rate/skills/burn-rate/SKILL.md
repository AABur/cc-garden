---
name: burn-rate
description: >-
  Audit Claude Code token spend, read-only, and rank where tokens are leaking.
  Deduplicated transcript analysis with skill/plugin/MCP/agent attribution,
  current 2026 pricing, ccusage baseline, and concrete fixes — no config is ever
  modified and nothing is written to disk.

  Use when the user asks to audit token usage, find token leaks, understand why
  they are hitting weekly limits, or optimize Claude Code spend.

  Trigger on: "/burn-rate", "burn rate", "token audit", "where are my tokens
  going", "why am I hitting limits", "optimize my Claude Code", "token leak".

  Skip when: the user wants a luck/retrospective reflection (use lucky-break or
  retro), or wants to APPLY config changes (this skill only diagnoses).
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py *) Read Grep
disallowed-tools: Edit Write
---

# Burn Rate — Read-Only Token-Spend Audit

> Concept and leak taxonomy adapted from *token-audit* by Bayram Annakov —
> https://github.com/BayramAnnakov/token-audit-skill. This is an independent
> implementation.

Find where Claude Code tokens are leaking — and what to fix first. Read-only:
no settings, CLAUDE.md, hooks, or skills are modified, and nothing is written to
disk. All analysis is local; the only network call is the optional `ccusage`
baseline.

## Workflow

### Step 1: Run the audit

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/audit.py" --days 7
```

`${CLAUDE_SKILL_DIR}` resolves to this skill's directory. If — and only if — the
command fails with "No such file or directory" (the variable did not expand),
locate the script with `find ~/.claude -path '*burn-rate*/scripts/audit.py' | head -1`
and run that path. Pass `--days N` to change the window (default 7).

### Step 2: Narrate the JSON as a report

Parse the JSON and write a tight report in the user's conversation language
(default English; for a Russian conversation, write the report in Russian — keep
technical terms like ccusage, /compact, CLAUDE.md, MCP untranslated).

Sections:
1. **Spend summary** — from `ccusage` (total, by model, trend). If `ccusage_error`
   is set, say so and proceed with token counts only.
2. **Where to look first (Pareto)** — from `bottlenecks`: top skills / plugins /
   agents / session-kinds by tokens. This is the attribution view the original
   skill lacks.
3. **Ranked leaks** — for each leak: severity badge (🔴 critical / 🟡 warning /
   🟢 suggestion), evidence bullets with numbers, tokens reclaimable + the fix.
4. **One fix to apply this week** — the single highest-leverage action.

### Step 3: Framing rules (read this)

- **Lead with tokens reclaimed/week and % category reduction**, not dollars.
- Most users are on a flat subscription — put `$` in parentheses labeled
  "reference only at API list pricing — your subscription is flat-fee", and
  translate to **plan headroom** where useful.
- Detector dollars are a **ranking signal**, not billing. The authoritative
  spend figure is the `ccusage` baseline.
- Note honestly: the 2k-token CLAUDE.md target is cited, not re-confirmed for
  2026; the "Opus on simple turns" signal uses output length as a weak proxy.

## What it does NOT do

- Never edits settings.json, CLAUDE.md, hooks, or skills.
- Never writes the report or any file to disk — chat output only.
- No network calls except the optional `ccusage` baseline.
