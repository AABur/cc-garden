# Prototype

**TL;DR:** Create new objects by *cloning* a configured prototypical instance, instead
of constructing from scratch.

**Category:** Creational

## When to use

- Construction is expensive but cloning is cheap.
- You have a small set of *configured shapes* you frequently instantiate slight
  variants of (preset characters in a game, default report templates, sample
  documents).
- The set of variants is large enough to be hard to encode as subclasses.
- You want to register prototypes by name and let callers ask for one without knowing
  the concrete class.

## When NOT to use (Pythonic alternatives first)

- **`copy.deepcopy(obj)` / `copy.copy(obj)`.** The standard library covers most
  cloning needs in one call.
- **`dataclasses.replace(obj, field=...)`.** For dataclass-shaped prototypes, replace
  produces a modified clone in one expression.
- **The variants encode genuine type differences.** A `dict[str, Callable]` factory
  registry is clearer than a prototype dispatcher.
- **You only have one prototype.** That is a module-level constant; clone with
  `deepcopy`.

## Canonical implementation

From `faif/python-patterns` (`patterns/creational/prototype.py`), abridged:

```python
from __future__ import annotations
from typing import Any

class Prototype:
    def __init__(self, value: str = "default", **attrs: Any) -> None:
        self.value = value
        self.__dict__.update(attrs)

    def clone(self, **attrs: Any) -> "Prototype":
        obj = self.__class__(**self.__dict__)
        obj.__dict__.update(attrs)
        return obj

class PrototypeDispatcher:
    def __init__(self) -> None:
        self._objects: dict[str, Prototype] = {}

    def register_object(self, name: str, obj: Prototype) -> None:
        self._objects[name] = obj

    def get_objects(self) -> dict[str, Prototype]:
        return self._objects
```

The Dispatcher (the upstream calls it Manager / Registry) is the indirection that lets
clients ask for "the default prototype" without naming a class.

## Real-world examples

- **`copy` module.** Python's stdlib treats cloning as a first-class operation; many
  libraries rely on it for "factory by example" workflows.
- **Django model `.copy()` patterns.** Custom `clone()` methods on heavyweight model
  instances avoid recreating audit trails / permissions.
- **Game / simulation engines.** Pre-configured units, prefabs, and templates are
  cloned on spawn rather than constructed (Unity prefab Instantiate, Unreal
  duplication).

## Refactor recipe

When constructors take 12 parameters and the same handful of combinations recur:

1. Define each common combination once (`DEFAULT`, `SMALL`, `LARGE`).
2. Provide a clone helper — typically just `copy.deepcopy(prototype)`.
3. Callers ask the registry/dispatcher for the prototype name they want and clone.
4. New presets are *added by registering*, not by extending the constructor.

For dataclass-shaped objects:

```python
from dataclasses import replace
modified = replace(DEFAULT, name="custom", size=42)
```

This is the modern Pythonic Prototype.

## Review checklist

- ✅ Clones are *independent* — mutating one does not affect the prototype or other
  clones (deep copy where needed).
- ✅ The set of named prototypes is documented; their semantic differences are clear.
- ✅ Where possible, dataclass + `replace()` or `copy.deepcopy` replaces hand-rolled
  cloning.
- ❌ `clone()` performs a shallow copy when nested mutable state would surprise the
  caller. Use `deepcopy`.
- ❌ The dispatcher has accumulated dozens of near-identical prototypes — this is a
  smell that the variation should be parameter-driven, not prototype-driven.
- ❌ Prototypes mutate over the program's lifetime; clones miss subsequent changes.
  Make prototypes immutable (frozen dataclass, tuple) and rebuild the dispatcher when
  config changes.
