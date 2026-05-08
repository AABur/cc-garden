# Servant

**TL;DR:** Provide common functionality to a group of unrelated classes through a
helper class, without forcing them to inherit from a common base.

**Category:** Behavioral

## When to use

- Multiple classes need the same operation, but they do not naturally share a base
  class.
- Inheritance would be a forced "is-a" lie; composition fits better.
- The servant operation depends on the *capabilities* of its argument (duck-typed
  protocol), not on a fixed type.

## When NOT to use (Pythonic alternatives first)

- **Free functions / module helpers.** In Python the entire stdlib uses this pattern
  without naming it (`math.dist(p1, p2)`, `os.path.join(*paths)`). Free functions are
  the most idiomatic Servant.
- **`functools.singledispatch`** for type-dispatched helpers — cleaner than `if
  isinstance` chains in a Servant method.
- **Protocols** to formalize the duck-typed interface the servant requires.
- **A Mixin** if you do want subclassing — but read `references/anti-patterns.md` on
  inheritance overuse first.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/servant.py`), abridged:

```python
import math

class Position:
    def __init__(self, x, y): self.x, self.y = x, y

class Circle:
    def __init__(self, radius, position: Position):
        self.radius = radius; self.position = position

class Rectangle:
    def __init__(self, width, height, position: Position):
        self.width = width; self.height = height; self.position = position

class GeometryTools:
    """Servant — provides services for multiple unrelated shape classes."""

    @staticmethod
    def calculate_area(shape):
        if isinstance(shape, Circle):    return math.pi * shape.radius ** 2
        elif isinstance(shape, Rectangle): return shape.width * shape.height
        else: raise ValueError("Unsupported shape")

    @staticmethod
    def move_to(shape, new_position: Position):
        shape.position = new_position
```

`Circle` and `Rectangle` do not share a base class. `GeometryTools` provides services
to both via type dispatch. A more Pythonic version uses `singledispatch`:

```python
from functools import singledispatch

@singledispatch
def calculate_area(shape):
    raise ValueError(f"Unsupported: {type(shape).__name__}")

@calculate_area.register
def _(shape: Circle): return math.pi * shape.radius ** 2

@calculate_area.register
def _(shape: Rectangle): return shape.width * shape.height
```

## Real-world examples

- **`os.path` module** — services on `str` paths.
- **`math` module** — services on numeric types.
- **`json.dumps(obj)`** — service that serializes any compatible object.
- **`pprint.pprint(x)`** — service for human-readable printing.

## Refactor recipe

When you would otherwise add the same method to several unrelated classes:

1. Extract the method into a free function or a `Servant` class with static methods.
2. If the method dispatches on argument type, use `functools.singledispatch`.
3. Document the *protocol* the servant expects (e.g., "requires a `.position`
   attribute with `.x`, `.y`").
4. Use `Protocol` to make the contract explicit if static type checking is in use.

## Review checklist

- ✅ The servant respects the served classes' encapsulation; it reads attributes, it
  does not poke at private state.
- ✅ Type dispatch is implemented with `singledispatch` rather than `if isinstance`
  chains.
- ✅ The protocol expected of arguments is documented or expressed via `Protocol`.
- ❌ The servant grows into a god module that knows about every class in the system.
- ❌ The "servant" is just a free function with extra ceremony. Drop the class.
- ❌ The servant class is instantiated, but holds no state — make its methods static
  or move them to a module.
