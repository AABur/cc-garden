# Flyweight

**TL;DR:** Share many fine-grained objects efficiently by storing the *intrinsic*
state once and passing *extrinsic* state at the call site.

**Category:** Structural

## When to use

- You instantiate huge numbers of objects with mostly identical state.
- The intrinsic (shared) state is large; extrinsic (per-context) state is small.
- Memory pressure is real and measurable.

## When NOT to use (Pythonic alternatives first)

- **`sys.intern()`** for strings — Python already de-duplicates short identifiers and
  exposes `intern()` for explicit pooling.
- **Pre-existing object pools.** For database connections, threads, etc., see
  `creational/pool.md` and library-specific pools.
- **Premature optimization.** Profile before applying Flyweight. The pattern adds
  complexity that only pays off at scale.
- **The objects are mutable per use.** Flyweight assumes the shared state is
  immutable; mutation breaks the invariant.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/flyweight.py`), abridged:

```python
import weakref

class Card:
    _pool: weakref.WeakValueDictionary = weakref.WeakValueDictionary()

    def __new__(cls, value: str, suit: str):
        key = value + suit
        obj = cls._pool.get(key)
        if obj is None:
            obj = object.__new__(Card)
            cls._pool[key] = obj
            obj.value, obj.suit = value, suit
        return obj
```

The `WeakValueDictionary` lets the GC reclaim entries no longer referenced elsewhere,
preventing the pool from leaking. `Card("9", "h")` returns the same object on
subsequent calls.

## Real-world examples

- **`sys.intern()`** — explicit string interning (cited in upstream docstring).
- **`fractions.Fraction` cache** for small rationals.
- **Game engines** sharing texture / mesh data across thousands of sprite instances.
- **AST literal caching** in interpreter implementations.

## Refactor recipe

When a profile shows millions of duplicate objects:

1. Identify the intrinsic vs extrinsic state. Intrinsic is what is duplicated;
   extrinsic is what varies.
2. Build a `_pool: WeakValueDictionary` keyed by intrinsic state.
3. Override `__new__` to return the pooled instance when keys match.
4. Move extrinsic state out of the object — pass it to methods, do not store on the
   instance.
5. Verify with a memory profile that the saving is real and worth the complexity.

## Review checklist

- Good: Intrinsic state is immutable after creation.
- Good: The pool uses weak references to avoid memory leaks (or has explicit eviction).
- Good: Memory savings are measured, not assumed.
- Bad: The "Flyweight" stores per-instance mutable extrinsic state — that defeats the
  pattern.
- Bad: Equality semantics (`__eq__`, `__hash__`) silently broken by interning. Verify.
- Bad: Pool is unbounded and never garbage-collected. Use weak references or eviction.
