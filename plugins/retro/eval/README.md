# /retro eval set

Trigger-accuracy evaluation for the `/retro` skill description.

## Files

- `trigger-eval.json` — 20 realistic queries, each tagged `should_trigger: true|false`. 10 positive cases (cover decision timeline, abandoned approaches, loops, F-rules, intent-vs-state, project archaeology, both ru/en) and 10 negative cases (near-misses with overlapping skills: claude-md-management, sprint retro, git log, find-docs, gen-test, new-python-project, brainstorming).

## Re-run the optimization loop

The `skill-creator` plugin ships a description optimization loop. To re-run after editing the description:

```bash
cd /Users/aabur/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator
python -m scripts.run_loop \
  --eval-set /Users/aabur/Documents/GitHub/AABur/cc-garden/plugins/retro/eval/trigger-eval.json \
  --skill-path /Users/aabur/Documents/GitHub/AABur/cc-garden/plugins/retro/skills/retro \
  --model claude-sonnet-4-6 \
  --max-iterations 5 \
  --verbose
```

The loop:
1. Splits the eval set 60/40 into train and held-out test.
2. Evaluates the current description (3 runs per query for stability).
3. Calls Claude to propose description tweaks based on failing cases.
4. Re-evaluates each new candidate. Picks the winner by **test** score (avoids overfitting to train).
5. Returns JSON with `best_description`. Apply manually to `SKILL.md`.

## Edit the eval set

Open `trigger-eval.json` and add/remove/edit items. Keep the format:

```json
[
  {"query": "realistic phrasing the user would type", "should_trigger": true, "note": "what this case covers"}
]
```

Realistic phrasing matters more than coverage breadth. A vague "do retro" is a weak case; a 3-sentence concrete prompt with project specifics is a strong case.
