# Specification

**TL;DR:** Encapsulate business rules as composable objects that can be combined with
boolean logic (`and`, `or`, `not`).

**Category:** Behavioral

## When to use

- Business rules need to be *first-class*: stored, combined, persisted, edited at
  runtime.
- Complex eligibility / filtering logic is built up dynamically (search builders,
  rule engines, access policies).
- The rules need to be unit-tested in isolation from the things they apply to.

## When NOT to use (Pythonic alternatives first)

- **Boolean expressions on plain functions returning bool.** `is_admin(user) and
  is_active(user)` is shorter than two `Specification` objects combined.
- **Closures.** A returned bool-producing callable composes naturally.
- **Library-provided filters** (SQLAlchemy filters, Django Q objects). Domain-tuned
  abstractions usually beat a generic Specification.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/specification.py`), abridged:

```python
from abc import abstractmethod

class Specification:
    @abstractmethod
    def is_satisfied_by(self, candidate) -> bool: ...

class CompositeSpecification(Specification):
    @abstractmethod
    def is_satisfied_by(self, candidate) -> bool: ...
    def and_specification(self, other): return AndSpecification(self, other)
    def or_specification(self, other):  return OrSpecification(self, other)
    def not_specification(self):        return NotSpecification(self)

class AndSpecification(CompositeSpecification):
    def __init__(self, one, other): self._one, self._other = one, other
    def is_satisfied_by(self, c):
        return bool(self._one.is_satisfied_by(c) and self._other.is_satisfied_by(c))

class OrSpecification(CompositeSpecification):
    def __init__(self, one, other): self._one, self._other = one, other
    def is_satisfied_by(self, c):
        return bool(self._one.is_satisfied_by(c) or self._other.is_satisfied_by(c))

class NotSpecification(CompositeSpecification):
    def __init__(self, wrapped): self._wrapped = wrapped
    def is_satisfied_by(self, c): return not self._wrapped.is_satisfied_by(c)
```

Concrete specs subclass `CompositeSpecification` and implement `is_satisfied_by`.
Combining them yields a tree of specifications that can be evaluated together. A
clean Pythonic variant overloads operators (`__and__`, `__or__`, `__invert__`) so
specs can be combined as `spec_a & spec_b | ~spec_c`.

## Real-world examples

- **SQLAlchemy `Query.filter`** + `or_`, `and_`, `not_` — domain-specific
  Specification.
- **Django `Q` objects** — composable query predicates.
- **Rule engines** (`durable-rules`, `experta`) — Specification-shaped APIs for fact
  matching.
- **Permission policies** in larger frameworks (Django Guardian, casbin).

## Refactor recipe

When a method is `if user.is_admin or (user.is_editor and user.is_active and not user.banned): ...`:

1. Extract each predicate into a Specification class (or a function returning bool).
2. Combine with `.and_specification(...)`, `.or_specification(...)`, or operator
   overloads.
3. Replace the call site with `spec.is_satisfied_by(user)`.
4. Add unit tests for each Specification in isolation.

## Review checklist

- ✅ Specifications are pure (no side effects); they only check.
- ✅ Combining specs preserves short-circuit semantics where it matters.
- ✅ Specs have stable, documented names matching domain language.
- ❌ A Specification has accumulated logic that *acts* on the candidate, not just
  evaluates it.
- ❌ Composition produces deeply nested objects with no `__repr__`; debugging is
  hard.
- ❌ Specifications duplicate filtering already supported by your ORM / query layer.
  Use the native filters.
