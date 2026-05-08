# Registry

**TL;DR:** Track all subclasses (or named instances) of a type in a central registry,
discoverable at runtime.

**Category:** Behavioral

## When to use

- Plugin systems where new implementations register themselves at import time.
- Class-based dispatch where you want to look up the right class by name without an
  explicit table.
- Auto-discovery patterns (every subclass of `Command` becomes a CLI subcommand).

## When NOT to use (Pythonic alternatives first)

- **Explicit `dict[str, type]`** is often clearer than a metaclass.
- **`__init_subclass__`** is the modern Pythonic way and generally beats a metaclass
  for registration; the metaclass machinery in the canonical example is heavyweight.
- **Entry points** (`pyproject.toml` `[project.entry-points]`) for cross-package
  plugin discovery.
- **Decorator-based registration**: `@register("my-thing")` is often clearer than
  metaclass magic.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/registry.py`), abridged:

```python
from typing import Dict

class RegistryHolder(type):
    REGISTRY: Dict[str, "RegistryHolder"] = {}

    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        cls.REGISTRY[new_cls.__name__] = new_cls
        return new_cls

    @classmethod
    def get_registry(cls):
        return dict(cls.REGISTRY)

class BaseRegisteredClass(metaclass=RegistryHolder):
    """Any subclass auto-registers."""
```

A modern Pythonic equivalent without metaclass:

```python
class BaseRegisteredClass:
    REGISTRY: dict[str, type] = {}

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        BaseRegisteredClass.REGISTRY[cls.__name__] = cls
```

`__init_subclass__` is more discoverable, less magical, and avoids metaclass conflicts
with frameworks like Django.

## Real-world examples

- **`pytest` plugin discovery** — fixtures and plugins register via decorators and
  entry points.
- **`click` commands** registered via `@cli.command()`.
- **Django apps registry** of installed apps and their models.
- **Marshmallow / Pydantic** custom field registration.

## Refactor recipe

When you have a growing `dict` mapping names to classes, manually maintained:

1. Decide between `__init_subclass__` (in-process), decorator-based registration, or
   entry points (cross-package).
2. Move registration logic into one place; remove manual updates.
3. Document the discovery mechanism and the contract subclasses must satisfy.
4. Add tests that confirm new subclasses appear in the registry without manual hooks.

## Review checklist

- ✅ Registration is automatic and traceable — a developer can grep for the
  registration point and find every entry.
- ✅ A subclass cannot accidentally fail to register (no silent skip).
- ✅ Subclass names are unique, or collisions are detected and raise.
- ❌ The registry is mutated outside the hook in surprising ways. Lock it down.
- ❌ Metaclass conflicts with framework base classes (Django models). Switch to
  `__init_subclass__`.
- ❌ Subclasses are imported only when "needed", and the registry is empty at startup
  because their modules never imported. Make registration eager via entry points or
  explicit imports.
