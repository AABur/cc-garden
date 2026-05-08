# Decorator (structural pattern, not the `@decorator` syntax)

**TL;DR:** Add behaviour to an object dynamically by wrapping it in another object
that has the same interface.

**Category:** Structural

> **Important distinction.** Python's `@decorator` syntax is the same idea applied to
> functions and classes. For most callable wrapping, the syntax is what you want — see
> `references/pythonic-alternatives.md`. The structural Decorator pattern is for
> wrapping *objects* (often non-callable) that need to expose the same interface.

## When to use

- You want to add behaviour (logging, caching, formatting, encryption) to an object
  without modifying its class.
- Multiple optional behaviours stack independently — boldface, italic, underline can
  combine.
- The object you are wrapping has a non-trivial interface (multiple methods); a
  function wrapper would not capture all of it.

## When NOT to use (Pythonic alternatives first)

- **Use `@decorator` for callables.** Hand-rolling a wrapper class around a single
  function is rarely the right choice in Python.
- **Inheritance fits.** If the augmentation is permanent and applies to all instances,
  subclass.
- **Single behaviour, single use.** Inline it.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/decorator.py`), abridged:

```python
class TextTag:
    def __init__(self, text: str): self._text = text
    def render(self) -> str: return self._text

class BoldWrapper(TextTag):
    def __init__(self, wrapped: TextTag): self._wrapped = wrapped
    def render(self) -> str: return f"<b>{self._wrapped.render()}</b>"

class ItalicWrapper(TextTag):
    def __init__(self, wrapped: TextTag): self._wrapped = wrapped
    def render(self) -> str: return f"<i>{self._wrapped.render()}</i>"

# Stacking
ItalicWrapper(BoldWrapper(TextTag("hello"))).render()
# '<i><b>hello</b></i>'
```

Each wrapper presents the same `render()` interface and adds its bit. Order of
wrapping determines order of nesting.

## Real-world examples

- **`io` streams.** `BufferedReader` wraps `RawIOBase`, `TextIOWrapper` wraps the
  buffer — each adds behaviour while keeping the file-like interface.
- **`functools.lru_cache`** — function decorator that adds caching; the syntax is
  Python's, but it embodies the structural pattern.
- **`gzip.GzipFile`** wraps a file-like object and adds compression on read/write.

## Refactor recipe

To add behaviour to an existing object class:

1. Define a wrapper class with the same interface as the wrapped class.
2. Hold the wrapped object as `self._wrapped`.
3. Forward each method, adding the new behaviour where appropriate.
4. (Optional) `__getattr__` for unmodified calls.
5. Compose at the call site — `B(A(obj))` stacks behaviours.

## Review checklist

- Good: The wrapper preserves the wrapped's interface (a `Protocol` or ABC if useful).
- Good: Wrappers compose without unexpected interactions.
- Good: For callables, `@decorator` syntax was considered first.
- Bad: The wrapper changes behaviour in surprising ways for unrelated methods. Keep
  augmentation focused.
- Bad: The "decorator" replaces the wrapped object's behaviour entirely — that is a
  Strategy or Adapter, not a Decorator.
- Bad: Stacking depth grows over time and diagnostics become impenetrable. Add `__repr__`
  that exposes the chain.
