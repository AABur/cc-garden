# Chaining Method (Fluent Interface)

**TL;DR:** Each method returns `self` (or another chainable object), allowing calls to
be chained together: `obj.do_a().do_b().finish()`.

**Category:** Behavioral

## When to use

- DSL-like APIs where reading the chain reads as a sentence.
- Configuration / query building where many small steps refine a single object.
- Method-chaining is the dominant idiom in your domain (SQL builders, HTTP clients).

## When NOT to use (Pythonic alternatives first)

- **Keyword-only args do the same job.** `Order(price=10, discount="ten_percent")`
  vs `Order().set_price(10).set_discount("ten_percent")`. The first is shorter and
  clearer.
- **Long chains harm debuggability.** Pdb cannot stop "between methods" easily; tracebacks
  cite the whole expression.
- **Side effects inside chains hide state changes.** If `obj.foo().bar()` mutates `obj`
  silently, callers cannot tell which method did what.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/chaining_method.py`), abridged:

```python
from __future__ import annotations

class Person:
    def __init__(self, name: str): self.name = name
    def do_action(self, action: Action) -> Action:
        print(self.name, action.name, end=" ")
        return action

class Action:
    def __init__(self, name: str): self.name = name
    def amount(self, val: str) -> Action:
        print(val, end=" ")
        return self
    def stop(self) -> None:
        print("then stop")

person = Person("Jack")
person.do_action(Action("move")).amount("5m").stop()
# Jack move 5m then stop
```

Each method returns either `self` or another chainable object. The chain ends with a
"terminal" method (here `stop()`) that returns `None`.

## Real-world examples

- **SQLAlchemy query API**: `session.query(User).filter(...).order_by(...).limit(10)`.
- **`pandas.DataFrame`**: `.groupby(...).agg(...).reset_index()`.
- **`requests.Session()`** and **`httpx.Client()`** with `.auth(...).headers(...)` style
  helpers in newer wrappers.
- **`pathlib.Path`** with `.parent.parent / "x.txt"` — operator chaining is the same
  idea via `__truediv__`.

## Refactor recipe

When you have many "set this, then set that" calls on the same object:

1. Decide if a `dataclass` with kwargs or a `replace()` would be clearer first.
2. If you really want chaining, change setters to `return self`.
3. Distinguish *building* (returns chainable) from *executing* (returns final result).
4. Add a `__repr__` that exposes the accumulated state, so debugging mid-chain is
   possible.

## Review checklist

- Good: Each chainable method has a clear non-`None` return (`self` or a child builder).
- Good: A terminal method exists and is documented as the chain's exit.
- Good: The chain is short enough to read in one breath. Long chains paginate badly.
- Bad: Chained methods raise without indicating which step failed; tracebacks cite the
  whole expression. Consider intermediate variables for diagnosis.
- Bad: The "chain" mutates global state, hiding side effects behind fluency.
- Bad: Chaining is preferred everywhere even when keyword args would be clearer.
