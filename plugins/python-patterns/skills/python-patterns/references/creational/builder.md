# Builder

**TL;DR:** Decouple the construction of a complex object from its representation, so the
same construction process can build different representations.

**Category:** Creational

## When to use

- Construction has *multiple steps* with intermediate validity. The object can be
  meaningfully poked at between steps (`builder.add_topping(...)` repeatedly, then
  `builder.bake()`).
- The *type of the final product* depends on accumulated state during construction
  (Director picks `ThinCrustPizza` vs `ThickCrustPizza` based on which methods were
  called).
- You want an immutable final product but a mutable construction phase.

## When NOT to use (Pythonic alternatives first)

- **Bag of fields with defaults.** Use `dataclass`:

  ```python
  from dataclasses import dataclass, field

  @dataclass
  class Pizza:
      crust: str
      sauce: str
      toppings: list[str] = field(default_factory=list)
  ```

  Combined with keyword-only args (`@dataclass(kw_only=True)`) you cover most "lots of
  parameters" cases without a builder.
- **Validation matters but the shape is flat.** `pydantic.BaseModel` or `attrs` give
  you defaults, validation, and `__repr__` for free.
- **Construction has a single step.** A factory function (`make_pizza(...)`) suffices.
- **No genuine intermediate validity.** If the partially-built object would never be
  observable to callers, the "step-by-step" framing buys nothing — just call the
  constructor.

## Canonical implementation

From `faif/python-patterns` (`patterns/creational/builder.py`), abridged:

```python
class Building:
    def __init__(self) -> None:
        self.build_floor()
        self.build_size()

    def build_floor(self): raise NotImplementedError
    def build_size(self): raise NotImplementedError
    def __repr__(self) -> str: return f"Floor: {self.floor} | Size: {self.size}"

class House(Building):
    def build_floor(self): self.floor = "One"
    def build_size(self):  self.size = "Big"

class Flat(Building):
    def build_floor(self): self.floor = "More than one"
    def build_size(self):  self.size = "Small"
```

The base class orchestrates the construction; subclasses fill in the steps. For
*director-driven* construction (where the director chooses the concrete class), the
upstream file pulls `construct_building(cls)` out of `__init__`:

```python
def construct_building(cls) -> Building:
    building = cls()
    building.build_floor()
    building.build_size()
    return building
```

## Real-world examples

- **`urllib3.PoolManager`** uses staged configuration before issuing requests — pool
  options, retries, and headers accumulate before the first call.
- **`Sphinx` document builders.** A `BuildEnvironment` assembles documents from
  multiple sources before emitting HTML.
- **Test fixtures.** "Given a User with these traits, then a Subscription, then…" —
  builder libraries like `factory_boy` formalize this.
- **`SQLAlchemy` query construction.** `query.filter(...).order_by(...).limit(...)` is
  builder-as-fluent-API; see also `behavioral/chaining_method.md`.

## Refactor recipe

When you find a constructor with 12 optional parameters:

1. **First check `dataclass`.** If the parameters are flat and independent, this is
   the fix. Stop here unless construction has stages.
2. If construction has stages, define a `Builder` class with one method per stage. The
   stage methods set attributes on `self._product`.
3. End with a `build()` method that returns the assembled product (often a
   `dataclass` or another immutable type). The builder itself can be reusable or
   one-shot.
4. (Optional) Add a `Director` for common build sequences:
   `house = HouseDirector(builder).build()`.

## Review checklist

- ✅ The builder's stages have *intermediate validity* — partial construction is
  meaningful, not arbitrary.
- ✅ The final product is constructed once, not mutated by callers thereafter.
- ✅ The builder makes the call site clearer than `dataclass(...)` would have.
- ❌ The builder wraps a `dataclass` with no value added. Delete the builder.
- ❌ Each stage just sets one attribute and could be a `dataclass` field. Same fix.
- ❌ The builder has shared state between calls and produces different results on
  successive `build()` calls. Either reset state in `build()` or document the
  one-shot contract.
