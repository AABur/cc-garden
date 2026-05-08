# Visitor

**TL;DR:** Add operations to a fixed object structure without modifying its classes.
Each operation is a Visitor with one method per concrete element type.

**Category:** Behavioral

## When to use

- You have a stable object structure (e.g., an AST) and want to add new operations
  without touching every node class.
- Operations are heterogeneous (rendering, validating, transforming) and each needs
  per-type logic.
- You expect to add *more operations* over time but few new node types.

## When NOT to use (Pythonic alternatives first)

- **`functools.singledispatch`** does the same job with less ceremony — register
  per-type handlers on a free function:
  ```python
  from functools import singledispatch
  @singledispatch
  def render(node): raise NotImplementedError
  @render.register
  def _(node: Number): return str(node.value)
  ```
- **Match statement (3.10+)** for one-off type dispatch sites.
- **Methods on the node classes themselves.** If you control the AST and operations
  are few, methods may be cleaner. Use Visitor when you do *not* want to touch the
  node classes for every new operation.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/visitor.py`), abridged:

```python
from typing import Union

class Node: pass
class A(Node): pass
class B(Node): pass
class C(A, B): pass

class Visitor:
    def visit(self, node, *args, **kwargs):
        for cls in node.__class__.__mro__:
            meth = getattr(self, "visit_" + cls.__name__, None)
            if meth:
                return meth(node, *args, **kwargs)
        return self.generic_visit(node, *args, **kwargs)

    def generic_visit(self, node, *args, **kwargs):
        print(f"generic_visit {type(node).__name__}")

    def visit_B(self, node, *args, **kwargs):
        print(f"visit_B {type(node).__name__}")
```

The visitor walks the node's MRO looking for a `visit_<Class>` method. This *extrinsic*
visitor avoids the Java pattern's "double dispatch" by leveraging Python's introspection.

## Real-world examples

- **Python's `ast.NodeVisitor`** — the textbook visitor (cited upstream).
- **`Black` formatter** ships its own AST visitor.
- **`pyflakes`, `mypy`, `flake8`** — all walk the AST via Visitor-shaped abstractions.
- **JSON / XML pretty-printers** that dispatch on node type.

## Refactor recipe

When a method on a class hierarchy is `if isinstance(node, A): ... elif ...`:

1. Decide between Visitor and `singledispatch` — the latter is usually simpler.
2. If you go with Visitor: define a `Visitor` class with `visit_<TypeName>` methods.
3. Either give nodes an `accept(visitor)` method (classical) or use the MRO-walking
   `visit(node)` from the canonical example (Pythonic).
4. New operations are new Visitor subclasses; node classes never change.

## Review checklist

- ✅ The visitor handles every concrete node type, or has a sensible
  `generic_visit` fallback.
- ✅ The dispatch is correct under multiple inheritance — explicit MRO walk handles
  this in the canonical implementation.
- ✅ For the simpler Pythonic equivalent, `singledispatch` was considered.
- ❌ The visitor mutates nodes during traversal in ways that break iteration. Buffer
  changes if needed.
- ❌ Adding a new node type requires changing every visitor — that is the visitor's
  known weak point. Consider whether the structure is really stable.
- ❌ The hierarchy has only two types and the dispatch is two `isinstance` checks.
  Inline.
