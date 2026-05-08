# python-patterns — Claude Code plugin

[![Patterns](https://img.shields.io/badge/patterns-36-blue)](#pattern-catalog)
[![Source](https://img.shields.io/badge/source-faif%2Fpython--patterns-success)](https://github.com/faif/python-patterns)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

A Claude Code plugin that gives the agent on-demand expertise in classical Gang-of-Four
and Python-specific design patterns, distilled from
[faif/python-patterns](https://github.com/faif/python-patterns) (42k+ stars). Optimized for
three real workflows: writing new code, refactoring existing code, and reviewing pull
requests.

> **Pythonic first.** The plugin biases toward plain Python — first-class functions,
> `dataclass`, generators, modules-as-singletons, `@decorator` syntax — and only suggests
> a classical pattern when the abstraction earns its keep. Singleton, God Object, and
> deep inheritance are flagged as anti-patterns.

---

## Installation

This plugin is published through the **cc-garden** marketplace. From inside Claude Code:

```
/plugin marketplace add AABur/cc-garden
/plugin install python-patterns
```

After installation the `python-patterns` skill auto-loads on relevant prompts. No slash
command — Claude triggers it whenever a Python design or review task matches.

---

## How it triggers

Claude consults this plugin when you:

- Name a pattern explicitly: *"make this a Factory"*, *"use Strategy here"*,
  *"refactor with Observer"*.
- Describe a problem the catalog solves: *"I have multiple algorithms for…"*,
  *"construct an object with 12 fields"*, *"decouple subsystem X"*,
  *"notify subscribers"*, *"undo/redo"*, *"state machine"*.
- Ask for design or code review: *"is this Pythonic?"*, *"this looks
  over-engineered"*, *"code review please"*, *"is this the right abstraction?"*.
- Are about to introduce an anti-pattern: *"make this a Singleton"* triggers a redirect
  to Borg or a module-level value, with reasoning.

It stays out of the way for framework-specific tasks (Django, FastAPI, SQLAlchemy
idioms), pandas/numpy data work, and one-shot scripts where patterns add nothing.

---

## What it does

- **New code.** Suggests the right pattern with a canonical implementation, plus the
  Pythonic alternative if one applies.
- **Refactoring.** Identifies code that warrants a pattern (long `if isinstance` chains,
  many constructor variants, hand-rolled event hooks) and proposes a step-by-step
  refactor recipe.
- **Code review.** Flags pattern misuse and anti-patterns, distinguishing between
  legitimate use and gratuitous OOP ceremony.

---

## Pattern catalog

Loaded on demand through progressive disclosure — only the relevant pattern's reference
file enters context.

### Creational (7)
abstract_factory · borg · builder · factory · lazy_evaluation · pool · prototype

### Structural (10)
3-tier · adapter · bridge · composite · decorator · facade · flyweight · front_controller
· mvc · proxy

### Behavioral (17)
chain_of_responsibility · catalog · chaining_method · command · interpreter · iterator ·
mediator · memento · observer · publish_subscribe · registry · servant · specification ·
state · strategy · template · visitor

### Testability
dependency_injection

### Fundamental
delegation_pattern

### Other (non-GoF)
blackboard · graph_search · hsm

### Anti-patterns (flagged, not implemented)
Singleton · God Object · inheritance overuse — see
`skills/python-patterns/references/anti-patterns.md`.

---

## Layout

```
python-patterns/
├── .claude-plugin/plugin.json
├── README.md
└── skills/python-patterns/
    ├── SKILL.md                       # router (always loaded body)
    └── references/
        ├── selection-guide.md         # problem → pattern lookup
        ├── pythonic-alternatives.md   # when classical is overkill
        ├── anti-patterns.md           # Singleton / God Object / inheritance
        ├── creational/                # 7 files
        ├── structural/                # 10 files
        ├── behavioral/                # 17 files
        ├── testability/               # dependency_injection
        ├── fundamental/               # delegation_pattern
        └── other/                     # blackboard, graph_search, hsm
```

---

## Attribution

Pattern descriptions, canonical examples, and "Examples in Python ecosystem" notes are
adapted from [faif/python-patterns](https://github.com/faif/python-patterns)
(MIT). Anti-pattern guidance derives from the same project's README.

The plugin's editorial bias — Pythonic-first, anti-pattern-aware, refactor-ready — is
authored for this distribution.

---

## License

MIT. See upstream [faif/python-patterns LICENSE](https://github.com/faif/python-patterns/blob/master/LICENSE)
for the source material.
