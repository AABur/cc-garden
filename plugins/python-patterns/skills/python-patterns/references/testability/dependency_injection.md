# Dependency Injection

**TL;DR:** Pass collaborators in (constructor, parameter, or setter) instead of
hard-coding them, so tests and alternative implementations can swap them.

**Category:** Testability / Fundamental

## When to use

- Tests need to substitute a collaborator (real DB → in-memory fake, real clock →
  frozen clock, real HTTP → recorded responses).
- The same code should run against multiple implementations (production vs sandbox,
  cloud A vs cloud B).
- Open/Closed principle — extending behaviour without modifying client code.

## When NOT to use (Pythonic alternatives first)

- **Don't reach for a framework.** Python rarely needs DI containers. Constructor
  injection is one extra parameter. Frameworks like `dependency-injector`,
  `injector`, etc. solve a problem most Python codebases do not have.
- **Module-level imports for stable dependencies.** If `from .config import settings`
  is imported once at app start and never swapped, that is fine. DI matters where
  swapping is real.
- **`unittest.mock.patch`** for surgical test-time substitution when refactoring to DI
  is too costly. It works; just be aware that patching couples tests to import paths.

## Canonical implementation

From `faif/python-patterns` (`patterns/dependency_injection.py`), three flavours,
abridged:

```python
from typing import Callable

class ConstructorInjection:
    """Pass the collaborator at construction. Most common; failure-fast."""
    def __init__(self, time_provider: Callable):
        self.time_provider = time_provider
    def get(self):
        return f"<span>{self.time_provider()}</span>"

class ParameterInjection:
    """Pass it per call. Stateless; useful for one-off uses."""
    def get(self, time_provider: Callable):
        return f"<span>{time_provider()}</span>"

class SetterInjection:
    """Set after construction. Avoid unless required by lifecycle."""
    def set_time_provider(self, time_provider: Callable):
        self.time_provider = time_provider
    def get(self):
        return f"<span>{self.time_provider()}</span>"
```

Constructor injection is the default. Parameter injection fits stateless utilities.
Setter injection only when lifecycle constraints force it (frameworks that build the
object before injecting), and accept the trade-off that the object can be in an
invalid state until the setter is called.

## Real-world examples

- **`pytest` fixtures.** A test parameter `def test_x(db):` is parameter injection by
  the framework.
- **`requests.Session` / `httpx.Client`.** Pass a session / client for testability.
- **`logging.Logger`.** `logger = logging.getLogger(__name__)` — receivers inject the
  logger at construction.
- **FastAPI's `Depends(...)`** — declarative parameter injection for routes.

## Refactor recipe

When code is hard to test because it instantiates its dependencies:

1. Identify the dependency: where does the class call `Database()`, `requests.get()`,
   `datetime.now()` directly?
2. Lift the dependency into a constructor parameter.
3. Default to the production value if convenience matters: `def __init__(self,
   db: Database | None = None): self.db = db or Database()`.
4. Tests pass an in-memory or fake dependency instead.
5. Document the contract the dependency must satisfy (`Protocol` or ABC).

## Review checklist

- Good: Dependencies are explicit at construction; no magic global lookups inside
  methods.
- Good: The contract for each injected dependency is documented or expressed as a
  `Protocol`.
- Good: Defaults are reasonable for production; tests do not mock everything.
- Bad: A "DI framework" was introduced when constructor parameters would do. Remove.
- Bad: Setter injection is used everywhere; many objects exist in half-initialized
  state. Promote to constructor injection.
- Bad: Tests rely on monkey-patching attributes the object instantiated for itself.
  That is brittle; restructure to inject.
