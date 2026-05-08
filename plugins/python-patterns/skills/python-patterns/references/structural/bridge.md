# Bridge

**TL;DR:** Decouple an abstraction from its implementation so the two can vary
independently.

**Category:** Structural

## When to use

- You have two dimensions of variation and a 2D class explosion looms (`CircleAPI1`,
  `CircleAPI2`, `RectAPI1`, `RectAPI2`, …). Bridge separates the dimensions: a Shape
  hierarchy *holds* a DrawingAPI rather than inheriting from one.
- You want to switch implementations at runtime (different rendering backends,
  different remote services).
- The abstraction's clients should not care which implementation is in use.

## When NOT to use (Pythonic alternatives first)

- **Composition is enough without naming the pattern.** Bridge is composition with a
  story; if you can hold an instance and delegate, you may already be applying it
  without ceremony.
- **Strategy is a better fit.** When the pluggable thing is a single algorithm rather
  than a family of operations forming an "implementation", see `behavioral/strategy.md`.
- **Single dimension of variation.** If only the implementation varies (no abstraction
  hierarchy), it is just dependency injection.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/bridge.py`), abridged:

```python
class DrawingAPI1:
    def draw_circle(self, x, y, r): print(f"API1.circle at {x}:{y} radius {r}")

class DrawingAPI2:
    def draw_circle(self, x, y, r): print(f"API2.circle at {x}:{y} radius {r}")

class CircleShape:
    def __init__(self, x, y, radius, drawing_api):
        self._x, self._y, self._radius = x, y, radius
        self._drawing_api = drawing_api

    def draw(self):  # delegates to the implementation
        self._drawing_api.draw_circle(self._x, self._y, self._radius)

    def scale(self, pct):  # operates on the abstraction
        self._radius *= pct
```

Two hierarchies — one of shapes (could grow: rectangles, triangles), one of APIs
(could grow: SVG, OpenGL, Canvas). They evolve independently. Without Bridge you
would have N×M classes.

## Real-world examples

- **`logging` handlers.** Loggers (abstraction) hold handlers (implementation); the
  same logger can write to file, syslog, network without subclassing.
- **`numpy` array types** wrapping different backends (CPU, GPU via CuPy).
- **GUI toolkits**: a `Window` holds a platform-specific renderer.

## Refactor recipe

When you see `ShapeAPI1`, `ShapeAPI2`, `ShapeAPI3` parallel hierarchies:

1. Pull the API methods into a `DrawingAPI` Protocol or class.
2. Make each `Shape` hold a `drawing_api` attribute instead of inheriting.
3. Inject the API at construction.
4. Delete the now-redundant `ShapeAPIN` classes; keep the API hierarchy and the Shape
   hierarchy as two separate trees.

## Review checklist

- Good: The two hierarchies vary genuinely independently; the cross-product is real.
- Good: Implementations satisfy a single, documented Protocol/ABC.
- Bad: Only one implementation exists and never plans to grow — Bridge is over-engineered;
  inject directly without naming the pattern.
- Bad: The abstraction reaches into implementation specifics, breaking the boundary.
  The Bridge is leaky; tighten the interface.
