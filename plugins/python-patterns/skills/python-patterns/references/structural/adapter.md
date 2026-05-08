# Adapter

**TL;DR:** Make an existing class's interface look like a different (expected)
interface, so it can plug into code that expects the latter.

**Category:** Structural

## When to use

- You have a third-party class with `do_thing()` and your code expects `process()`.
- You want to wrap legacy classes to fit a new contract without modifying them.
- You need to expose a uniform interface over a heterogeneous set of underlying
  classes (`Dog.bark`, `Cat.meow`, `Car.make_noise(level)` → all become
  `obj.make_noise()`).

## When NOT to use (Pythonic alternatives first)

- **Subclass and add the method.** When you control the source, just add the method.
- **Duck typing.** If the consumer only needs *one* method, define it as a function or
  pass a callable; do not introduce an Adapter class.
- **Monkey-patch with care.** For a third-party class you cannot subclass, *sometimes*
  patching `MyClass.process = MyClass.do_thing` is acceptable in tightly-scoped tests.
  Avoid in production.
- **`functools.partial` is enough.** If the adaptation is just "call this with a fixed
  arg", `partial` is the answer.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/adapter.py`), abridged:

```python
from typing import Any, Callable, TypeVar
T = TypeVar("T")

class Adapter:
    """Adapts an object by replacing methods.

    dog = Dog()
    dog = Adapter(dog, make_noise=dog.bark)
    """
    def __init__(self, obj: T, **adapted_methods: Callable[..., Any]) -> None:
        self.obj = obj
        self.__dict__.update(adapted_methods)

    def __getattr__(self, attr: str) -> Any:
        return getattr(self.obj, attr)
```

The trick: `__getattr__` forwards everything not explicitly adapted. The adapter is
*one* generic class for many adaptations; the variation lives in the keyword
arguments at construction.

## Real-world examples

- **Grok framework** uses adapters extensively (cited in upstream docs).
- **`logging.LoggerAdapter`** — adds context (extra fields) to log calls without
  changing call sites.
- **`socket.socket` SSL/TLS wrapping.** `ssl.wrap_socket(s)` returns an SSL-capable
  adapter over a plain socket.
- **`io.TextIOWrapper`** wraps a binary stream and presents a text interface.

## Refactor recipe

To adapt a third-party class to a new interface:

1. Identify the *consumer's* required interface — what methods does it call?
2. Write a thin adapter class that holds the third-party object and exposes the
   required methods, delegating internally.
3. (Optional) Use `__getattr__` for pass-through of unrelated calls.
4. Replace direct uses with the adapter where the new interface is needed.

## Review checklist

- ✅ The adapter exposes the required interface and *only* that — no creep into
  the third party's surface.
- ✅ The adapter delegates rather than re-implementing; behaviour stays in the
  adaptee.
- ❌ The "adapter" wraps an object with the same interface. That is a Decorator
  (adds behaviour) or a Proxy (controls access). See those references.
- ❌ The adapter accumulates state of its own that should belong to the adaptee.
  Push state into the adaptee or extract it.
- ❌ Multiple adapters wrap each other unintentionally. Layer documentation
  matters; collapse if the chain is incidental.
