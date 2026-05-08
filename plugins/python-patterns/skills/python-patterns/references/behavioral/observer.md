# Observer

**TL;DR:** Maintain a list of dependents and notify them of state changes.

**Category:** Behavioral

## When to use

- One subject; many dependents that should react to its state changes.
- Dependents register / unregister at runtime.
- The subject does not need to know who is listening, only that there is a way to
  notify.

## When NOT to use (Pythonic alternatives first)

- **A list of callables.** For simple notification, `subject.callbacks: list[Callable]`
  with `for cb in callbacks: cb(event)` is enough. The Observer *class* hierarchy is
  often ceremony.
- **Framework signals.** Django Signals, Flask Blinker — use them; do not roll your
  own (cited in upstream docstring).
- **Pub-sub broker.** When many publishers and subscribers exist with topic routing,
  see `behavioral/publish_subscribe.md`.
- **`asyncio` events / queues** for async-native flows.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/observer.py`), abridged:

```python
from __future__ import annotations
from typing import List

class Observer:
    def update(self, subject: Subject) -> None: pass

class Subject:
    _observers: List[Observer]
    def __init__(self): self._observers = []
    def attach(self, observer): 
        if observer not in self._observers:
            self._observers.append(observer)
    def detach(self, observer):
        try: self._observers.remove(observer)
        except ValueError: pass
    def notify(self):
        for observer in self._observers:
            observer.update(self)

class Data(Subject):
    def __init__(self, name: str = ""):
        super().__init__()
        self.name = name
        self._data = 0

    @property
    def data(self) -> int: return self._data

    @data.setter
    def data(self, value: int):
        self._data = value
        self.notify()
```

Setting `data.data = 5` triggers `notify()`, which calls `observer.update(self)` on
each registered observer.

## Real-world examples

- **Django Signals** — `pre_save`, `post_save`, `m2m_changed` (cited upstream).
- **Flask Blinker signals**.
- **`tkinter` variable traces**: `var.trace_add("write", callback)`.
- **`pytest` hooks** — plugins observe test lifecycle events.
- **Async `asyncio.Event` / `asyncio.Condition`** as native primitives.

## Refactor recipe

When you have a class that periodically wants to "tell others" something:

1. **Try a list of callables first.** If the registration / lifecycle of observers is
   simple, that is the answer.
2. If observers need to remember per-subject state or implement multiple update
   methods, lift to an Observer class.
3. Add `attach` / `detach` methods to the Subject.
4. Whenever state changes, call `self.notify()` from the setter (or wherever).
5. Decide on observer lifecycle: weak references (so a forgotten observer can be GC'd)
   vs strong (so the Subject prevents collection).

## Review checklist

- Good: `attach` is idempotent (no double-registration).
- Good: `notify` does not propagate exceptions from a buggy observer to the Subject —
  decide on isolation policy.
- Good: Observers are not added during iteration of the observer list (or are buffered
  to avoid mutation-during-iteration).
- Bad: Observer references are strong and never released — leaks. Consider
  `weakref.WeakSet`.
- Bad: Notification ordering matters but is not guaranteed. Document the contract.
- Bad: A simple list of callbacks would have sufficed; Observer ceremony is overkill.
