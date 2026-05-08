# Delegation

**TL;DR:** An object handles a request by forwarding it to a delegate (held by
composition) instead of inheriting the behaviour.

**Category:** Fundamental

## When to use

- "Has-a" relationship where you want to expose some of the held object's behaviour
  to clients of the holder.
- You need to add behaviour to a third-party class without subclassing.
- You want to model "behaves-like-X for these calls, my-own-thing for the rest"
  cleanly.

## When NOT to use (Pythonic alternatives first)

- **Plain composition** without `__getattr__` magic. Just hold the object and call
  `self.delegate.foo()` when needed. Magic delegation hides which calls actually go
  to the delegate, which can confuse callers.
- **Subclassing**, *if* "is-a" is honestly true. See
  `references/anti-patterns.md` for when it is not.
- **Mixins** for cross-cutting capabilities — but read the anti-patterns guide on
  inheritance overuse first.

## Canonical implementation

From `faif/python-patterns` (`patterns/fundamental/delegation_pattern.py`),
abridged:

```python
from __future__ import annotations
from typing import Any, Callable

class Delegator:
    def __init__(self, delegate: Delegate) -> None:
        self.delegate = delegate

    def __getattr__(self, name: str) -> Any | Callable:
        attr = getattr(self.delegate, name)
        if not callable(attr):
            return attr
        def wrapper(*args, **kwargs):
            return attr(*args, **kwargs)
        return wrapper

class Delegate:
    def __init__(self) -> None: self.p1 = 123
    def do_something(self, something: str, kw=None) -> str:
        return f"Doing {something}{kw or ''}"
```

`Delegator` does not inherit from `Delegate`. Calls and attribute reads that are not
defined on `Delegator` fall through to `self.delegate` via `__getattr__`. The
`Delegator` can override or extend behaviour by defining its own methods.

## Real-world examples

- **`logging.LoggerAdapter`** delegates to a `Logger` while injecting context.
- **`collections.UserDict`, `UserList`, `UserString`** are subclassing helpers, but
  the same effect via composition + delegation is common in third-party libraries.
- **Many ORM "Manager" classes** delegate to a query-set object.
- **`weakref.proxy`** delegates while maintaining a weak reference.

## Refactor recipe

When you find yourself reaching for inheritance to "share helpers" or "add a method
or two":

1. Stop. Verify it is "is-a", not "has-a".
2. Hold the would-be parent as an attribute: `self.delegate = ParentLikeObject()`.
3. For methods you want to expose unchanged, add explicit thin delegating methods
   (preferred for clarity) — or implement `__getattr__` to forward unknown calls
   (preferred for terseness, with the trade-off of magic).
4. Add your own methods on the delegator without touching the delegate.

## Review checklist

- Good: Delegation is preferred over inheritance unless "is-a" is true.
- Good: The delegate's interface is documented or formally typed (`Protocol`).
- Good: Magic `__getattr__` delegation is used judiciously; when in doubt, prefer
  explicit thin methods so introspection (IDE completion, mypy) works.
- Bad: The delegator's surface differs from the delegate's in surprising ways. Make
  the boundary explicit.
- Bad: Multiple layers of `__getattr__` chains; debugging becomes archaeology.
- Bad: Used as a workaround for genuinely needed inheritance (LSP-relevant subtyping).
  Use inheritance there, sparingly.
