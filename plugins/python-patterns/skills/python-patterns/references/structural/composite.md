# Composite

**TL;DR:** Treat individual objects and compositions of objects uniformly through a
common interface.

**Category:** Structural

## When to use

- Part-whole hierarchies (file system: file/folder, GUI: widget/container, expression
  tree: literal/operator).
- Clients should not care whether they are operating on a leaf or a group.
- Operations recurse naturally: `render`, `size`, `total`, `fold`.

## When NOT to use (Pythonic alternatives first)

- **Duck typing handles it.** If both leaves and composites already expose `render()`,
  no formal Composite pattern is needed — the structure is implicit.
- **Flat collection is enough.** If there is no nesting, you have a list, not a tree.
- **The abstraction is forced.** If composite operations are not natural ("what does
  `print(folder)` even do?"), do not flatten leaves and groups under one interface.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/composite.py`), abridged:

```python
from abc import ABC, abstractmethod

class Graphic(ABC):
    @abstractmethod
    def render(self) -> None: ...

class Ellipse(Graphic):
    def __init__(self, name): self.name = name
    def render(self): print(f"Ellipse: {self.name}")

class CompositeGraphic(Graphic):
    def __init__(self): self.graphics: list[Graphic] = []
    def add(self, g): self.graphics.append(g)
    def remove(self, g): self.graphics.remove(g)
    def render(self):
        for g in self.graphics:
            g.render()
```

`CompositeGraphic` *is a* `Graphic`, so a composite can contain composites. Recursion
is in the structure, not in the call site.

## Real-world examples

- **`pathlib.Path`** treats files and directories with a unified API (though
  composition of subpaths is implicit).
- **`xml.etree.ElementTree`** — elements have child elements; iterating is uniform.
- **GUI frameworks** (`tkinter` Frame containing Frames containing Widgets).
- **AST**. `ast.Module` contains statements which contain expressions; visitors walk
  the tree uniformly.

## Refactor recipe

When code branches on "is this a single thing or a list of things":

1. Define a `Component` interface (Protocol or ABC) with the operation.
2. Make the leaf class implement the interface naively.
3. Make a Composite class that holds children and forwards the operation to each.
4. Remove the branch — clients just call `component.operation()`.

## Review checklist

- ✅ The shared operation makes sense for both leaves and composites.
- ✅ Adding/removing children is in the composite, not exposed to the leaf interface
  (or transparently as no-ops if you must — but document the contract).
- ❌ The composite leaks list operations through the interface; clients couple to
  internals.
- ❌ Leaves are forced to implement no-op `add` / `remove` to satisfy the interface,
  raising errors at runtime. Use a separate Composite class.
- ❌ The hierarchy has hidden cycles (a child composite contains an ancestor) — guard
  if cycles are possible, or document acyclic invariant.
