# Chain of Responsibility

**TL;DR:** Pass a request along a chain of handlers; each decides whether to handle it
or forward it to the next.

**Category:** Behavioral

## When to use

- You have multiple potential handlers and the right one is determined at runtime.
- The chain order matters — the first capable handler wins.
- You want to add/remove/reorder handlers without changing their code.
- Cross-cutting concerns are layered (auth → validation → business logic → logging).

## When NOT to use (Pythonic alternatives first)

- **Dispatch dict.** If the chosen handler depends on a *single* discriminator value,
  a `dict[key, handler]` is clearer than a chain.
- **`functools.singledispatch`** for dispatch on type.
- **The chain is a list and you process *all* of them.** That is just iteration.
- **Framework middleware.** Django, Flask, ASGI all already model their request
  pipeline as a chain — use the framework's hooks.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/chain_of_responsibility.py`),
abridged:

```python
from abc import ABC, abstractmethod
from typing import Optional

class Handler(ABC):
    def __init__(self, successor: Optional["Handler"] = None):
        self.successor = successor

    def handle(self, request: int) -> None:
        res = self.check_range(request)
        if not res and self.successor:
            self.successor.handle(request)

    @abstractmethod
    def check_range(self, request: int) -> Optional[bool]: ...

class ConcreteHandler0(Handler):
    @staticmethod
    def check_range(request: int) -> Optional[bool]:
        if 0 <= request < 10:
            print(f"handler 0: {request}")
            return True
        return None
```

The base class encodes the chain mechanics; subclasses only define
`check_range`. Handlers can be assembled at runtime: `h0.successor = h1; h1.successor = h2`.

## Real-world examples

- **Django middleware** — each middleware can short-circuit the chain by returning a
  response (cited in upstream docstring).
- **logging handlers / filters** — log records flow through filters that can drop or
  modify them.
- **`webob`/`werkzeug` request processing** — middleware-as-callable WSGI chains.
- **Event bubbling** in GUI frameworks (Tk, Qt) where unhandled events propagate to
  parents.

## Refactor recipe

When a long `if/elif` cascade decides which of N processors to run:

1. Make each branch its own handler class (or callable).
2. Each handler decides "can I handle this?"; if not, calls the next.
3. Wire the chain in one place (often at app startup).
4. Add a fallback handler at the end so the chain is closed.
5. Optionally, log when handlers decline so debugging stays sane.

## Review checklist

- ✅ Each handler has a single responsibility — "match this case, otherwise pass".
- ✅ The chain has a deterministic order, configured in one place.
- ✅ A fallback handler covers the "no one matched" case.
- ❌ Two handlers in the chain can both match; behaviour silently depends on order.
  Make the contract explicit: first match wins.
- ❌ The chain is constructed lazily inside handlers — opaque flow. Build it explicitly.
- ❌ Used where a dispatch dict would suffice; the chain is cargo-cult middleware.
