# 🪙 Lucky Break — Your Weekly Luck Break

[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)
[![Forked from](https://img.shields.io/badge/forked%20from-coin--flip-success)](https://github.com/BayramAnnakov/coin-flip-skill)
[![Ritual](https://img.shields.io/badge/ritual-weekly-blue)](#how-it-triggers)

A Claude Code plugin that analyzes your last 7 days of conversations — across both
**Claude Code** and **Codex CLI** — and suggests **one** actionable, pattern-breaking
thing to do, grounded in the neuroscience of luck. Best run as a Sunday-evening ritual.

---

## Installation

This plugin is published through the **cc-garden** marketplace. From inside Claude Code:

```
/plugin marketplace add AABur/cc-garden
/plugin install lucky-break@cc-garden
```

---

## How it triggers

Run it deliberately, as a weekly luck-break ritual:

```
/lucky-break
```

Claude also reaches for it when you ask for a weekly reset or a nudge out of autopilot
— *"what should I change this week?"*, *"give me a pattern break"*, *"flip a coin on
my week"*, *"I feel stuck in a routine"*. Best used as a **Sunday-evening ritual** so
the week ahead starts with one intentional departure from the gray straight path.

It stays out of the way for ordinary build, debug, and ship work — it is a reflection
tool, not a coding assistant.

---

## What it does

1. Scans your conversation transcripts from the last 7 days across all projects, in
   both Claude Code (`~/.claude/projects`) and Codex CLI (`~/.codex/sessions`). Each
   project is tagged with its `source`, so the same repo worked on through both CLIs
   is read together. (Reading Codex logs needs only the files — not a running Codex.)
2. Extracts your messages to map topics, cognitive mode (exploit vs. explore), and
   excitement signals.
3. Identifies your "gray straight path" — what you do on autopilot, even when it is
   productive.
4. Finds unfinished threads — fascination signals that got buried under operational
   work.
5. Suggests **one** specific, actionable thing to do this week.

---

## The Idea

Lucky people aren't born lucky. They run different neurological software — and it can
be installed. Nobuko Nakano identifies five mechanisms:

1. **Self-narrative** — declaring "I am lucky" shifts the prefrontal cortex from
   threat-detection to opportunity-recognition mode.
2. **Biology** — serotonin production requires morning sunlight, tryptophan, and
   regular sleep.
3. **Fascination compass** — dopamine responds to genuine interest, not obligation.
   "Each small departure from routine is a ticket in a lottery that the cautious never
   enter."
4. **Authentic generosity** — genuine giving activates the brain's reward center more
   powerfully than receiving.
5. **Persistence** — game theory simulations show outcomes overwhelmingly favor those
   who stay in the game.

This plugin reads your recent Claude Code and Codex CLI sessions, identifies your "gray
straight path" (the routine you're on autopilot with, even if it's productive), finds
buried fascination signals, and suggests one concrete pattern-break for the week.

---

## Example Output

```
🪙 Your luck break this week:

Have a 30-minute conversation with someone outside your field. No agenda.

Why: Your last 7 days were 100% exploit mode across 15 projects.
Every interaction was transactional — students, customers, team, leads.
The only pure-curiosity thread lasted 3 messages before you got interrupted.

The gray path: Build → ship → write about it → adapt → ship again.

Fascination signal: Two non-work reading items have survived 4 weeks
of inbox triage without being deleted or acted on.
```

---

## The Science

Based on Nobuko Nakano's "Lucky People" (Gallery UK, 2026) and supported by:

- **Cascio et al. (2016)** — self-affirmation activates the medial prefrontal cortex.
- **DeYoung (2013)** — dopamine as the neuromodulator of exploration.
- **Levitt (2020)** — random coin flips help overcome status quo bias by 25%.
- **Mauboussin, "The Success Equation"** — result = skill + luck; only skill is
  controllable.

---

## Credits

**lucky-break is a fork of, and based on, the original
[coin-flip](https://github.com/BayramAnnakov/coin-flip-skill) skill by Bayram
Annakov.** This distribution reworks coin-flip into a cc-garden plugin while preserving
its concept, the five luck mechanisms, and the research grounding.

The concept was inspired by [this post](https://t.me/ProductsAndStartups/1718) about
Nobuko Nakano's research on the behavioral neuroscience of luck.

---

## License

MIT. This fork preserves the original author's copyright alongside the derivative
author's — see [`LICENSE`](./LICENSE) for both copyright lines.
