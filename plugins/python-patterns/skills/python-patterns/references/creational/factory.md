# Factory (Factory Method)

**TL;DR:** Delegate the creation of an instance to a function or method, so callers do
not couple to a specific class.

**Category:** Creational

## When to use

- The concrete class to instantiate depends on a runtime value (config, user input,
  feature flag).
- You want to keep the construction logic in *one place* so all sites that produce the
  object see the same defaults / wiring.
- You need to evolve construction (add a step, swap a class, log creations) without
  touching every call site.

## When NOT to use (Pythonic alternatives first)

- **You only ever instantiate one class.** Just call `MyClass(...)`.
- **The "factory" is one-line and called once.** Inline it.
- **The dispatch is a fixed table.** A `dict[str, type]` lookup is often clearer than
  a function with `if/elif` chains:

  ```python
  LOCALIZERS: dict[str, type] = {"en": EnglishLocalizer, "el": GreekLocalizer}
  loc = LOCALIZERS[lang]()
  ```

  The "factory function" form is appropriate when construction is more than a single
  class lookup.
- **You wanted Abstract Factory.** If you need a *family* of related products to vary
  together, see `creational/abstract_factory.md`.

## Canonical implementation

From `faif/python-patterns` (`patterns/creational/factory.py`), abridged:

```python
from typing import Dict, Protocol, Type

class Localizer(Protocol):
    def localize(self, msg: str) -> str: ...

class GreekLocalizer:
    def __init__(self) -> None:
        self.translations = {"dog": "σκύλος", "cat": "γάτα"}
    def localize(self, msg: str) -> str:
        return self.translations.get(msg, msg)

class EnglishLocalizer:
    def localize(self, msg: str) -> str:
        return msg

def get_localizer(language: str = "English") -> Localizer:
    localizers: Dict[str, Type[Localizer]] = {
        "English": EnglishLocalizer,
        "Greek":   GreekLocalizer,
    }
    return localizers.get(language, EnglishLocalizer)()
```

The `Localizer` `Protocol` gives static type checkers a structural interface; concrete
classes need not inherit from it.

## Real-world examples

- **Django's `formset_factory`** returns a class tailored to user-provided arguments
  (extras, max forms, etc.). Cited by the upstream module docstring.
- **`logging.getLogger(name)`** is a factory for `Logger` instances, returning the
  same logger for the same name and creating new ones on demand.
- **`pathlib.Path(...)`** dispatches to `PosixPath` or `WindowsPath` based on the host
  OS — a factory hidden behind the constructor.
- **`asyncio.get_event_loop()` / `asyncio.new_event_loop()`** factory functions over a
  family of loop implementations.

## Refactor recipe

When `if isinstance(...)` chains are spread across the codebase deciding *which class
to construct*:

1. Move the conditional to one function: `def make_thing(kind, **kw): ...`.
2. Replace `if/elif` with a dispatch dict where possible.
3. Update call sites to call `make_thing(...)` instead of `if kind == "X": X(...)`.
4. If the function grows complex, split per-class factories with a registry:
   `REGISTRY: dict[str, Callable[..., Thing]]`.

## Review checklist

- ✅ The factory's signature documents what callers must supply; defaults make sense.
- ✅ Construction logic that should not be repeated lives *only* in the factory.
- ✅ The `Protocol` (or ABC) the factory returns is honest — all returned classes
  satisfy it.
- ❌ The factory is one line returning `MyClass(*args)` and called from one place.
  Delete the factory.
- ❌ The factory uses `if isinstance` on a *class object* (`if cls is Dog: ...`); the
  dispatch dict is better.
- ❌ Multiple factories return slightly different shapes — callers cannot rely on the
  return type. Either tighten the contract (`Protocol`, `ABC`) or split into distinct
  named factories.
