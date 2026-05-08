# Lazy Evaluation

**TL;DR:** Delay the evaluation of an expression until its value is needed, and cache
the result so subsequent reads do not re-compute.

**Category:** Creational

## When to use

- The computation is expensive (DB query, network call, heavy CPU work).
- It may not be needed for every code path that constructs the object.
- The value is *stable* once computed (pure function of the instance's other state) —
  caching is safe.

## When NOT to use (Pythonic alternatives first)

- **`functools.cached_property` already does this.** In modern Python (3.8+), this is
  the answer for 95% of "lazy property" cases. Reach for the upstream pattern only when
  you need extra control (custom invalidation, descriptor that does *not* cache, etc.).

  ```python
  from functools import cached_property

  class Report:
      @cached_property
      def heavy_table(self) -> list[dict]:
          return self._compute()
  ```

- **Value depends on mutable state.** Caching gives stale results. Use a normal
  `@property` and let it re-evaluate on each access — or build an explicit cache with
  invalidation.
- **You want module-level laziness.** `importlib.util.LazyLoader` and PEP 562's
  module-level `__getattr__` cover that; do not roll your own.

## Canonical implementation

From `faif/python-patterns` (`patterns/creational/lazy_evaluation.py`), two equivalent
forms — descriptor and decorator-over-`@property`:

```python
import functools
from typing import Callable, Type

class lazy_property:
    """Descriptor: computes once, replaces itself with the value on the instance."""
    def __init__(self, function: Callable) -> None:
        self.function = function
        functools.update_wrapper(self, function)

    def __get__(self, obj, type_=None):
        if obj is None:
            return self
        val = self.function(obj)
        obj.__dict__[self.function.__name__] = val
        return val

def lazy_property2(fn: Callable) -> property:
    """Decorator over @property using a hidden attribute."""
    attr = "_lazy__" + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr):
            setattr(self, attr, fn(self))
        return getattr(self, attr)
    return _lazy_property

class Person:
    def __init__(self, name): self.name = name

    @lazy_property
    def relatives(self) -> str:
        # Pretend this is expensive.
        return "Many relatives."
```

Both forms cache the result on the instance. The descriptor form is faster on
subsequent access because it bypasses the property machinery and reads directly from
`__dict__`.

## Real-world examples

The upstream module references the same descriptor pattern in production code:

- **bottle** — [`lazy_property`](https://github.com/bottlepy/bottle).
- **django** — [`cached_property`](https://github.com/django/django/blob/main/django/utils/functional.py).
- **pip**, **pyramid**, **werkzeug** all ship variations.

The Python standard library's `functools.cached_property` (3.8+) consolidates these
into one canonical helper.

## Refactor recipe

To lazy-load an existing eager attribute:

1. Move the computation out of `__init__` into a method or property.
2. Decorate it with `@cached_property` (preferred) or the project's `lazy_property`
   helper.
3. Verify thread-safety needs. `cached_property` is *not* thread-safe per docs; if
   multiple threads can race the first access, use a lock or `functools.lru_cache`
   with `maxsize=None` on a method instead.
4. Drop any `if self._x is None:` guard from getters that the cached property now
   replaces.

## Review checklist

- Good: The cached value is a pure function of the instance's other (immutable) state.
- Good: `cached_property` is preferred over hand-rolled descriptors unless there's a
  reason.
- Good: Tests cover the "first access" and "second access" paths and confirm the
  computation runs only once.
- Bad: The cache is invalidated by mutation of *upstream* attributes but no
  invalidation is implemented. Either invalidate or do not cache.
- Bad: The descriptor returns `self` from `__get__` only on the class (not the instance)
  to allow introspection — verify this when a third-party tool inspects the property.
- Bad: Two threads can reach the first access simultaneously; resolve with a lock if
  the computation is non-idempotent.
