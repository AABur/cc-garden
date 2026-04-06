---
name: new-python-project
description: >-
  Initialize a new Python project from scratch with full tooling setup.
  Use whenever the user wants to create, start, initialize, bootstrap, or set up
  a new Python project — even if they just say "new project", "start a project",
  "create a Python app", or "I want to build X in Python". Covers the full stack:
  copier-astral template, uv, ruff, pytest (pure, no unittest), Google docstrings,
  gtm time tracking, GitHub private repo, branch protection, feature-branch workflow,
  and project CLAUDE.md.
---

# New Python Project Setup

Bootstrap a production-ready Python project end-to-end. Follow all 7 steps in order.

---

## Step 1 — Prerequisites Check

Run these checks before doing anything else:

```bash
copier --version
gh auth status
gtm --version
```

If any tool is missing, stop and show the user how to install it:

| Tool | Install |
|------|---------|
| copier | `pipx install copier` |
| gh CLI | `brew install gh` then `gh auth login` |
| gtm | `brew tap memcrab/gtm https://github.com/memcrab/gtm.git && brew install memcrab/gtm/gtm` |
| gtm (migrate from old tap) | `brew uninstall gtm && brew untap git-time-metric/gtm && brew cleanup` then run the command in the row above |

---

## Step 2 — Gather Project Info

Ask the user for (or infer from context):

- **Project name** — human-readable (e.g. "My Awesome Tool")
- **Short description** — one sentence
- **Python version** — default `3.12`
- **License** — default `MIT`
- **Include CLI?** (Typer-based) — default yes
- **Include Docker?** — default no
- **Include Docs?** (MkDocs) — default yes

Derive `project_slug` from project name: lowercase, spaces → hyphens, remove special chars.
The GitHub repo name and directory name both use `project_slug`.

---

## Step 3 — Create Project from Template

```bash
copier copy --trust gh:ritwiktiwari/copier-astral ./<project_slug>
cd <project_slug>
git init
```

The template will interactively ask for the parameters gathered in Step 2.
The template already sets up: uv, ruff, pytest, pre-commit, gitleaks, semgrep, GitHub Actions, git-cliff, Renovate.

---

## Step 4 — Post-Template Customizations

### 4a. Replace .gitignore with Toptal version

```bash
curl -s "https://www.toptal.com/developers/gitignore/api/python" > .gitignore
```

Then append gtm-specific ignores:
```bash
printf "\n# gtm time tracking\n.gtm/\ngtm.notes\n" >> .gitignore
```

### 4b. Configure pytest in pyproject.toml

Find the `[tool.pytest.ini_options]` section and ensure it has:

```toml
[tool.pytest.ini_options]
addopts = "--strict-markers --cov=src --cov-report=term-missing --cov-fail-under=80"
testpaths = ["tests"]
```

Coverage threshold is set to **80%** — pytest will fail if coverage drops below this.

### 4c. Configure ruff for Google docstrings and pytest rules

In the `[tool.ruff.lint]` section, ensure these rule sets are in `select`:
- `"D"` — pydocstyle (docstring conventions)
- `"PT"` — flake8-pytest-style (enforces pure pytest)

Add or update these sections:

```toml
[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["D"]  # No docstring requirement in tests
```

Key PT rules that enforce no-unittest:
- **PT009** — use `assert` instead of `assertEqual`, `assertTrue`, etc.
- **PT027** — use `pytest.raises` instead of `assertRaises`

These make unittest-style assertions a lint error.

### 4d. Create CLAUDE.md for the project

Read the template from `references/conventions.md` and generate `CLAUDE.md` in the project root,
substituting the actual project values (name, package name, etc.).

---

## Step 5 — Initialize Tooling

```bash
uv sync --dev
pre-commit install
gtm init
```

After `gtm init`, remind the user:
> Install the gtm plugin for your editor to enable time tracking:
> https://github.com/git-time-metric/gtm#editor-plugins

---

## Step 6 — GitHub Setup

### Create private repo and push

```bash
gh repo create <project_slug> --private --source=. --remote=origin --push
```

If the initial commit hasn't happened yet:
```bash
git add -A
git commit -m "feat: initial project setup from copier-astral template"
git push -u origin main
```

### Set branch protection on main

Prevent direct pushes to main — all changes must go through a PR:

```bash
gh api "repos/AABur/<project_slug>/branches/main/protection" \
  --method PUT \
  --header "Accept: application/vnd.github+json" \
  -f "required_status_checks=null" \
  -f "enforce_admins=false" \
  -f "required_pull_request_reviews[required_approving_review_count]=0" \
  -f "restrictions=null"
```

This requires a PR for every merge but doesn't require a reviewer approval (solo dev).

---

## Step 7 — Final Checklist

Display this checklist to the user:

```
Project <project_slug> is ready!

GitHub: https://github.com/AABur/<project_slug>

Next steps:
  [ ] Install gtm editor plugin: https://github.com/git-time-metric/gtm#editor-plugins
  [ ] Verify CI passes: gh run list --repo AABur/<project_slug>
  [ ] Start first feature branch:
        git checkout -b feat/<feature-name>

Feature branch workflow:
  1. Work on feat/<name> branch
  2. Commit in small, logical conventional commits
      feat: / fix: / docs: / test: / refactor: / config: / chore:
  3. Before merging: gh pr create
  4. Security review: uv run semgrep --config=auto . && git log | head -20
  5. Merge via PR (no direct push to main)
```

---

## Test Structure Convention (important!)

Tests must mirror the application code structure:

```
src/
  mypackage/
    auth/
      login.py        → tests/auth/test_login.py
    api/
      routes.py       → tests/api/test_routes.py
```

This is enforced by convention (documented in CLAUDE.md), not by tooling.

---

## What NOT to do

- Never use `unittest.TestCase` — use plain pytest functions and fixtures
- Never use `unittest` assertions (`assertEqual`, `assertTrue`, etc.) — use plain `assert`
- Never write tests in `TestCase` subclasses
- Never commit directly to `main`
- Never write Russian in any project file (code, docs, comments, commits)
