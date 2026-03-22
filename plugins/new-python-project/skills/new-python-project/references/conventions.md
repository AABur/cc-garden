# CLAUDE.md Template for New Python Projects

When creating CLAUDE.md for a new project, use this template.
Replace `<PROJECT_NAME>`, `<PACKAGE_NAME>` with actual values.

---

```markdown
# <PROJECT_NAME>

## Language
English everywhere: code, comments, docstrings, commit messages, docs. No exceptions.

## Project Structure
```
src/
  <PACKAGE_NAME>/     # application code
tests/                # mirrors src structure exactly
docs/                 # MkDocs documentation
```

## Testing
- pytest ONLY — no unittest, no TestCase subclasses
- Test location mirrors source location:
    src/<PACKAGE_NAME>/auth/login.py → tests/auth/test_login.py
- Run tests: `uv run pytest`
- Coverage threshold: 80% (enforced — tests fail below this)
- Never use: assertEqual, assertTrue, assertRaises — use plain assert and pytest.raises

## Code Style
- Docstrings: Google style (required for all public functions/classes/modules)
- Type hints: required for all public function signatures
- Comments: minimal — only where the logic is genuinely non-obvious
- Formatter/linter: ruff (run: `uv run ruff check .` and `uv run ruff format .`)

## Git Workflow
1. Create feature branch: `git checkout -b feat/<name>`
2. Commit in small, logical chunks using conventional commits:
   - `feat:` new functionality
   - `fix:` bug fix
   - `docs:` documentation only
   - `test:` tests only
   - `refactor:` no behavior change
   - `config:` configuration
   - `chore:` maintenance
3. Before merging: `gh pr create` (no direct push to main)
4. Security review before publishing: `uv run semgrep --config=auto .`

## Commands
```bash
uv sync --dev          # install all dependencies
uv run pytest          # run tests
uv run ruff check .    # lint
uv run ruff format .   # format
uv run semgrep --config=auto .  # security scan
gh run list            # check CI status
```

## Verification Workflow
After implementing changes: run `uv run pytest` and show output before committing.
Do not mark a task complete without verifying tests pass.
```
```

---

## Pytest Best Practices Reference

Source: https://pytest-with-eric.com/pytest-best-practices/pytest-organize-tests/

### Best Practice 2: Test Structure Mirrors Application Code

Every test file corresponds to exactly one source module:

```
src/myapp/
  __init__.py
  models/
    user.py          → tests/models/test_user.py
    product.py       → tests/models/test_product.py
  services/
    auth.py          → tests/services/test_auth.py
  api/
    endpoints.py     → tests/api/test_endpoints.py
```

Rules:
- Test file name = `test_` + source file name
- Test directory structure = source directory structure
- One test file per source module (can split into multiple if file grows too large)
- `conftest.py` files go in the directory where their fixtures are needed

### Pure pytest Style (no unittest)

```python
# WRONG — unittest style
import unittest

class TestUser(unittest.TestCase):
    def test_create(self):
        self.assertEqual(user.name, "Alice")

# RIGHT — pure pytest
def test_create_user():
    user = create_user("Alice")
    assert user.name == "Alice"

# WRONG — unittest exception testing
with self.assertRaises(ValueError):
    ...

# RIGHT — pytest style
import pytest
with pytest.raises(ValueError):
    ...
```
