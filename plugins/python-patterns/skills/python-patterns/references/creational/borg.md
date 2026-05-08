# Borg (Monostate)

**TL;DR:** Multiple instances that share state — same `__dict__` across every
instance — instead of restricting to one instance.

**Category:** Creational

> **Anti-pattern alert.** If the user asked for a Singleton, read
> `references/anti-patterns.md` first. Borg is the *redirect*; before implementing it,
> tell the user *why* it is preferred and confirm they actually need shared state, not
> a module-level value.

## When to use

- You need "one logical configuration, accessible from many call sites" *and* you also
  need each access point to look like a normal instance (e.g., for subclassing or for
  swapping in tests).
- Multiple subsystems should observe identical state, but you want the freedom to
  construct them at different times in different places.
- Subclassing matters: each Borg subclass can have its own `_shared_state`, so a
  `WindowsConfig` Borg and a `LinuxConfig` Borg coexist without colliding.

## When NOT to use (Pythonic alternatives first)

- **A module-level value is enough.** If you do not need an instance interface, just
  define `state = {}` at module top level. Imports give you sharing.
- **You are reaching for "global state" in disguise.** Borg is one logical state with
  many doorways; "global state for unrelated things" is just a global. Be honest about
  which it is.
- **Tests will be a problem.** Borg state survives across tests unless you explicitly
  reset `_shared_state`. If your test suite cannot stomach that, dependency injection
  (`testability/dependency_injection.md`) is a cleaner answer.

## Canonical implementation

From `faif/python-patterns` (`patterns/creational/borg.py`), abridged:

```python
class Borg:
    _shared_state: dict = {}

    def __init__(self) -> None:
        self.__dict__ = self._shared_state

class Config(Borg):
    def __init__(self, theme: str = None) -> None:
        super().__init__()
        if theme is not None:
            self.theme = theme

c1 = Config(theme="dark")
c2 = Config()
c2.theme  # "dark" — same __dict__
c1 is c2  # False — distinct instances
```

The trick is one line: `self.__dict__ = self._shared_state`. Every instance points at
the same dict, so attribute writes via `c1.x = 1` are visible to `c2.x`.

## Real-world examples

- **Database connection helpers** that need shared cursor / pool state across instances
  while still presenting an instance-shaped API to callers (the upstream README cites
  [pythonDbTemplate](https://github.com/onetwopunch/pythonDbTemplate/blob/master/database.py)).
- **Configuration objects** in long-lived applications where the config can be mutated
  at runtime (feature flags, hot reload) and every consumer must see the new value.

## Refactor recipe

Replacing a Singleton with Borg:

1. Remove the `_instance` / `__new__` ceremony.
2. Add `_shared_state: dict = {}` as a class attribute.
3. In `__init__`, set `self.__dict__ = self._shared_state` *before* any other
   attribute assignment.
4. Move "first-time initialization" guards into `__init__` itself (e.g.,
   `if "config" not in self.__dict__: self.config = load_default()`).
5. Audit subclasses: each subclass needs its own `_shared_state` if you want that
   subclass's instances to share *separately*.

## Review checklist

- ✅ The `__dict__ = _shared_state` line is in `__init__`, not `__new__`.
- ✅ Each subclass that wants its own state declares its own `_shared_state` class
   attribute.
- ✅ The choice of Borg over a module value is justified — there is a real reason to
   use the instance interface (subclassing, swap-in-test, etc.).
- ❌ `_shared_state` is mutated outside `__init__` in surprising ways. The "first
   time" branch should be obvious in code.
- ❌ Tests rely on Borg state but do not reset it between cases. Add a fixture that
   clears `_shared_state` per test.
- ❌ The codebase has *many* Borgs serving as a thin replacement for global
   variables. That is a design smell — consider dependency injection.
