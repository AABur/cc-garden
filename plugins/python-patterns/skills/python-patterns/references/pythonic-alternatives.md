# Pythonic alternatives — when plain Python beats the classical pattern

Many GoF patterns exist because Java, C++, or C# lack features Python has. In those
cases the classical pattern is *correct* in its home language and *ceremonial overhead*
in Python. Read this file before reaching for a class hierarchy.

The goal is **honest trade-offs**: do not ban patterns, but do not import them by reflex.

---

## First-class functions vs Strategy / Command / simple Factory

In Java, "an algorithm you can swap at runtime" requires a `Strategy` interface and a
class per variant. In Python, functions are values; assigning a function to a variable
*is* the strategy.

```python
# Strategy classes — Java-style
class SortStrategy:
    def sort(self, xs): ...

class QuickSort(SortStrategy):
    def sort(self, xs): ...

# Pythonic
sorter = sorted                       # built-in
sorter = lambda xs: sorted(xs, key=..., reverse=...)
sorter = my_custom_sort_function

# Strategy table
ALGORITHMS = {
    "quick": quick_sort,
    "merge": merge_sort,
    "tim": sorted,
}
result = ALGORITHMS[user_choice](data)
```

Reach for the Strategy *class* only when:

- The variants need persistent state across calls (e.g., a streaming algorithm with
  internal counters).
- They share enough boilerplate that base-class factoring is worth it.
- You need to introspect them at runtime (list available strategies, validate inputs)
  in ways a function cannot serve.

Otherwise, callables + a registry dict is the pythonic Strategy.

The same logic applies to **Command** (a callable plus its bound args is a `partial` or
a closure) and the simplest **Factory** (a function returning an instance).

---

## `functools.partial` and closures vs Command

```python
# Classical Command
class SendEmailCommand:
    def __init__(self, to, body): self.to, self.body = to, body
    def execute(self): smtp.send(self.to, self.body)

# Pythonic
import functools
cmd = functools.partial(smtp.send, "alice@example.com", "hi")
cmd()  # execute
```

Use the Command class only when you also need *undo*, *serialization*, *logging*, or
queueing infrastructure that benefits from an explicit object. See
`behavioral/command.md` for that case.

---

## `dict[str, Callable]` vs Catalog / Registry / Chain of Responsibility

A dispatch table replaces a chain of `if user.role == "admin"` cleanly:

```python
HANDLERS = {
    "admin":   handle_admin,
    "editor":  handle_editor,
    "viewer":  handle_viewer,
}
HANDLERS.get(user.role, handle_default)(request)
```

Promote to **Chain of Responsibility** only when handlers must run *in order* and *each
gets to decide* whether it handles or passes. A flat dict is wrong if order matters or
if multiple handlers can claim the same input.

Promote to **Registry** only when the table needs to be discoverable across modules
(third-party plugins, decorator-based registration). See `behavioral/registry.md`.

---

## `dataclass` vs Builder

`dataclass` (or `attrs`, or `pydantic`) gives you keyword-only construction, defaults,
validation, and `__repr__` for free.

```python
# Telescoping ctors / Builder
class Pizza:
    def __init__(self, crust, sauce, cheese=None, pepperoni=None,
                 mushrooms=None, olives=None, ...): ...

# Pythonic
from dataclasses import dataclass, field

@dataclass
class Pizza:
    crust: str
    sauce: str
    cheese: str | None = None
    toppings: list[str] = field(default_factory=list)
```

Reach for **Builder** when:

- Construction has *steps* that produce intermediate validity (you can call
  `add_topping(...)` repeatedly, then `bake()`).
- The thing being built is *immutable* once finished, but you want a mutable shape
  during construction.
- You need to switch which concrete class you build at the end ("director" choosing
  between `ThinCrust` vs `ThickCrust` based on accumulated state).

For a flat bag of fields, `dataclass` wins.

---

## `@property` and `functools.cached_property` vs Lazy Evaluation

The classical Lazy Evaluation pattern wraps an attribute in a class with a `__get__`
descriptor. Python's standard library already provides this:

```python
from functools import cached_property

class Report:
    @cached_property
    def heavy_table(self) -> list[dict]:
        return self._compute()  # runs once, cached on the instance
```

The full lazy-evaluation pattern (`creational/lazy_evaluation.md`) is worth reading for
context, but in modern code you are almost always better off with `@cached_property`.

---

## `@decorator` syntax vs structural Decorator pattern

Python's `@decorator` is *the* Decorator pattern, applied to functions and classes.
You almost never need a wrapper class.

```python
# Pythonic Decorator: wrap with extra behaviour
def with_retry(times=3):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            for attempt in range(times):
                try: return fn(*a, **kw)
                except TransientError:
                    if attempt == times - 1: raise
        return wrapper
    return deco

@with_retry(times=5)
def fetch(): ...
```

Reach for the wrapper-class form (see `structural/decorator.md`) only when:

- You need to expose the wrapper's own state (e.g., metrics) externally.
- The wrapped object is *not callable* — e.g., wrapping a file-like object so it
  decompresses on read; here a class implementing the same interface is natural.

---

## Generators vs Iterator

Implementing `__iter__` + `__next__` + `StopIteration` book-keeping is rarely worth it.
A generator function does the same work with a fraction of the code:

```python
# Hand-rolled iterator
class Counter:
    def __init__(self, n): self.n = n; self.i = 0
    def __iter__(self): return self
    def __next__(self):
        if self.i >= self.n: raise StopIteration
        self.i += 1
        return self.i - 1

# Pythonic
def counter(n):
    yield from range(n)
```

Reach for the explicit iterator class only when you need to *peek*, *reset*, *fork*, or
otherwise step outside the linear-consumption contract a generator provides.

---

## Module-level value vs Singleton

Already covered in `anti-patterns.md`, but the pattern bears repeating: if you need
"one logical thing", define it at module top level. Imports give you sharing.

---

## Composition / delegation vs deep inheritance

Inheritance signals "is-a". Most things you reach inheritance for are "has-a" or "uses".
See `fundamental/delegation_pattern.md` for the explicit pattern. The short form: if the
subclass overrides most of its parent's methods, it should not have inherited from the
parent in the first place.

---

## ABCs and `Protocol` vs explicit interface classes

`abc.ABC` plus `@abstractmethod` gives you nominal interfaces; `typing.Protocol` gives
you structural ("duck") interfaces. The classical "interface class" pattern from Java is
done with these — no third-party machinery needed.

```python
from typing import Protocol

class Localizer(Protocol):
    def localize(self, msg: str) -> str: ...
```

Any class with a matching `localize` method satisfies `Localizer`. No explicit
inheritance, no registration step.

---

## Decision flow

When the user describes a design problem, walk this list before reaching for a pattern:

1. **Is it a function?** A callable variable swap, a closure, or `partial` will do.
2. **Is it a dispatch table?** `dict[key, callable]` solves a lot.
3. **Is it a `dataclass`?** Most "small bundle of fields" needs are met here.
4. **Is it a generator / `cached_property` / `@decorator`?** Built-ins replace whole
   patterns.
5. **Only then** reach into `references/<category>/<pattern>.md`.

This ordering does not weaken the catalog. It applies the upstream README's own advice:
ask *why* before *how*.
