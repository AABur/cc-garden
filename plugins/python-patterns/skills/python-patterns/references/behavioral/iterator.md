# Iterator

**TL;DR:** Sequentially access elements of a container without exposing its underlying
representation.

**Category:** Behavioral

## When to use

- You have a custom container and want it to support `for x in container`.
- You need to expose iteration semantics that differ from the container's native
  shape (filtered, transformed, paginated).
- You want to support multiple simultaneous iterators over the same container.

## When NOT to use (Pythonic alternatives first)

- **Generators.** `def __iter__(self): yield from ...` covers most cases. Hand-rolling
  `__init__ + __next__ + StopIteration` book-keeping is rarely worth it.
- **Built-in iterables.** Lists, dicts, sets, files — they already iterate.
- **`itertools`.** `chain`, `groupby`, `islice`, `takewhile` cover transforms.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/iterator.py`) — the modern Pythonic
form is just a generator:

```python
def count_to(count: int):
    """Counts by word numbers, up to a maximum of five."""
    numbers = ["one", "two", "three", "four", "five"]
    yield from numbers[:count]

for n in count_to(3):
    print(n)
# one / two / three
```

The repo also ships an alternative implementation (`iterator_alt.py`) showing the
explicit `__iter__` / `__next__` form for educational purposes — it is rarely the
right answer in Python.

## Real-world examples

- **`os.scandir`** returns an iterator over directory entries.
- **`csv.reader`** yields rows lazily.
- **`itertools` module** — every helper there is an iterator factory.
- **Database cursors** — fetchone / fetchmany expose iterator semantics.

## Refactor recipe

When you have a `get_all()` that returns a list and the list is large:

1. Convert it to a generator: `yield` instead of `result.append`.
2. Update callers — most `for x in get_all()` loops keep working with no change.
3. Remove explicit list construction in callers that simply iterated.
4. If callers did `len(result)` or random access, they need the list; preserve a
   `list(...)` wrapper at those sites.

## Review checklist

- Good: A generator beats a hand-rolled iterator class unless there is a specific reason
  not to.
- Good: The iterator is exhausted exactly once; if multiple passes are needed, document
  it (e.g., return a callable factory or a fresh iterator each time).
- Good: `__iter__` returns *self* (or a new iterator) consistently with the contract.
- Bad: The hand-rolled iterator forgets to raise `StopIteration` on exhaustion. Use a
  generator.
- Bad: The iterator silently mutates the underlying container during iteration. Document
  or copy.
- Bad: Iteration order is implementation-dependent (e.g., over a `dict` pre-3.7) but
  callers assume otherwise.
