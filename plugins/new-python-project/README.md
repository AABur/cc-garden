# new-python-project

A Claude Code skill that bootstraps a production-ready Python project end-to-end.

## What it does

Runs a guided 7-step workflow:

1. **Prerequisites check** — verifies `copier`, `gh`, `gtm` are installed
2. **Gather project info** — name, description, Python version, license
3. **Create from template** — [copier-astral](https://github.com/ritwiktiwari/copier-astral) (uv, ruff, pytest, pre-commit, security scanning, CI/CD)
4. **Customize config** — Toptal gitignore, pytest 80% coverage, ruff Google docstrings, no-unittest enforcement
5. **Init tooling** — `uv sync --dev`, `pre-commit install`, `gtm init`
6. **GitHub setup** — private repo, branch protection on main, initial push
7. **Checklist** — gtm editor plugin reminder, CI verification, first feature branch

## Stack

| Tool | Purpose |
|------|---------|
| [copier-astral](https://github.com/ritwiktiwari/copier-astral) | Project template |
| [uv](https://github.com/astral-sh/uv) | Package manager |
| [ruff](https://github.com/astral-sh/ruff) | Linter + formatter |
| [pytest](https://pytest.org) | Testing (pure pytest, no unittest) |
| [gtm](https://github.com/Memcrab/gtm) | Git time tracking |
| [gh CLI](https://cli.github.com) | GitHub automation |

## Install

```
/plugin install new-python-project@cc-garden
```

## Usage

Just say: **"new python project"**, **"create a Python app"**, or **"initialize a project"** — the skill activates automatically.
