# Memento

**TL;DR:** Capture and externalize an object's internal state so it can be restored
later, without violating encapsulation.

**Category:** Behavioral

## When to use

- Undo / rollback support tied to *snapshots* rather than inverse actions (contrast
  with `behavioral/command.md`).
- Transactions that roll back on failure.
- Save/restore game state, document state, configuration state.
- Long-running workflows that need checkpoints.

## When NOT to use (Pythonic alternatives first)

- **`copy.deepcopy(obj)`** is the simplest memento; restore by `obj.__dict__.update(saved)`.
- **`dataclasses.replace`** for immutable snapshots.
- **DB transactions** if the state lives in the DB. Do not reinvent.
- **JSON / dataclass serialization** for full-state persistence to disk in safe
  formats.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/memento.py`), abridged:

```python
from copy import copy, deepcopy

def memento(obj, deep: bool = False):
    state = deepcopy(obj.__dict__) if deep else copy(obj.__dict__)
    def restore():
        obj.__dict__.clear()
        obj.__dict__.update(state)
    return restore

class Transaction:
    """Syntactic sugar around a memento closure."""
    def __init__(self, deep: bool, *targets):
        self.deep = deep
        self.targets = targets
        self.commit()
    def commit(self):
        self.states = [memento(t, self.deep) for t in self.targets]
    def rollback(self):
        for s in self.states:
            s()
```

The `memento` function returns a *closure* that knows how to restore. `Transaction`
groups several mementos for multi-object rollback.

## Real-world examples

- **Editor undo via state snapshots** (text editors that save the whole document
  state each step).
- **Form state in web frameworks** stored in session and restored on validation
  failure.
- **Database transactions / SAVEPOINTs** — DB-level mementos.
- **Time-travel debugging tools** that snapshot program state at each step.

## Refactor recipe

When you need rollback on exception:

1. Decide whether snapshot (Memento) or inverse-action (Command) fits — Memento is
   easier when actions are not naturally invertible.
2. Wrap critical sections in a context manager that captures state on enter and
   restores on exception.
3. For mutable shared state, use `deepcopy` to avoid aliasing.
4. Document the cost — deepcopy can be expensive for large objects.

## Review checklist

- Good: The memento captures *all* state needed for restoration. Partial snapshots cause
  bugs.
- Good: Deep vs shallow copy is chosen consciously based on aliasing risk.
- Good: The restore path is exercised by tests, not just the happy path.
- Bad: The memento exposes the saved state to callers, breaking encapsulation —
  externalize, but keep opaque.
- Bad: The save/restore cost is unbounded; large objects with many checkpoints will
  exhaust memory.
- Bad: Mementos hold references to mutable parts that change after capture, silently
  invalidating the snapshot.
