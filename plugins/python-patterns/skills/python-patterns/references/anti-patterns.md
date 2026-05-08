# Anti-patterns in Python — flag, explain, redirect

The upstream `faif/python-patterns` README explicitly lists three patterns as
**not recommended in Python**. This file gives the deeper "why" and the redirect.
Read it any time the user asks for one of these — do not silently implement.

## 1. Singleton

> "Ensure a class has only one instance, and provide a global point of access to it."
> — GoF, 1994

### Why this is wrong in Python

- **Modules are already singletons.** Every import gets you the same module object;
  binding `state = {}` at module top level is one of the simplest, most idiomatic
  shared-state patterns in Python. There is no "second instance" of a module.
- **Class-level `_instance` games hurt testability.** Patching the singleton in tests
  bleeds across test cases unless you remember to reset it. Pytest fixtures with
  function scope cannot save you if `MyService._instance` survives.
- **They invite hidden coupling.** Anyone, anywhere, can call
  `MyService.instance().foo()`. You lose the ability to swap implementations, inject
  fakes, or run two instances side-by-side (e.g., for a multi-tenant scenario you
  did not anticipate).
- **They are an OOP retrofit of a global variable.** Python lets you have global
  variables. Hiding the global behind a class does not remove the global; it adds
  ceremony.

### Redirects in order of preference

1. **Module-level value.** If you need exactly one configured object, define it at
   module scope. Imports give you sharing for free.
   ```python
   # registry.py
   _items: dict[str, Item] = {}

   def register(item: Item) -> None: _items[item.key] = item
   def lookup(key: str) -> Item: return _items[key]
   ```
2. **Borg.** When you really need *N* instances that share state (e.g., distinct API
   clients that all read the same config), use Borg — see
   `creational/borg.md`. Different instances, identical `__dict__`, no
   gate-keeping ceremony.
3. **Dependency injection.** Construct the object once at the application's edge
   (`main()`, app factory) and pass it in. See
   `testability/dependency_injection.md`. This is the answer when the real concern
   is "how do all my consumers find this object?".

### Detection cues

```python
class _Foo:
    _instance = None

    def __new__(cls, *a, **kw):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *a, **kw)
        return cls._instance
```
or `class Foo(metaclass=SingletonMeta):` or a `get_instance()` classmethod gating a
private constructor. All of these are anti-pattern smoke; flag them.

### When the user *insists* on Singleton

Implement Borg and explain that:
- It satisfies the invariant ("all instances behave identically") via shared state.
- It plays nicely with subclassing (each subclass can have its own state-pool).
- It does not bypass `__init__`, so initialization logic still runs predictably.

If they refuse Borg too, write the explicit `_instance` version, but leave a comment
recording the decision and the reasons it is fragile.

---

## 2. God Object

> One class that knows about, instantiates, and orchestrates everything in the program.

### Why it hurts

- **Diff-noise.** Every change to anything touches this class.
- **Untestable.** You cannot exercise one behaviour without spinning up the whole world.
- **Hard to reason about.** Reading a 1500-line class to find the three lines relevant to
  your bug is brutal.
- **Deters splitting.** Once everything imports `God.thing`, breaking `God` apart
  triggers ripples through the whole codebase. The longer it lives, the more expensive it
  becomes to remove.

### Detection cues

- Single class with > 7–10 distinct responsibilities (count public methods that do not
  share data — each cluster is a candidate class).
- Methods that take wildly different argument types because the class "handles
  everything".
- A constructor that wires up many unrelated subsystems.
- Imports from across the codebase all reaching into one class for unrelated reasons.

### Redirects

1. **Extract by responsibility.** Group methods that share data into their own class.
   Coupling within a class should be high; if half the methods do not touch the same
   attributes, those methods belong elsewhere.
2. **Composition over collection.** Replace `class Manager: ...` with smaller objects
   the manager *holds* and delegates to — see `fundamental/delegation_pattern.md`.
3. **Facade if the API really is wide.** If the surface needs to stay broad for
   external users, expose a facade that delegates to focused internal classes — see
   `structural/facade.md`. The facade is a *thin* router, not the implementation.

---

## 3. Inheritance overuse

> Deep `class Child(Parent(GrandParent(GreatGrand)))` chains, or inheriting purely to
> pull in helpers.

### Why it hurts

- **Brittle base.** A change in the deepest base class can break grandchildren you do
  not even remember exist (the *fragile base class problem*).
- **Mismatch with reality.** "is-a" relationships are rare. Most subclassing in the wild
  models "uses" or "has-a" — composition, not inheritance.
- **Method resolution order surprises.** Multiple inheritance + Python's MRO produces
  ordering that is correct but counterintuitive; bugs hide in the diamond.
- **Tightly couples lifetime.** A subclass shares its parent's interface, attributes,
  and lifecycle whether or not it wants to.

### Detection cues

- A base class added "to share `_log()` / `_validate()` / `_paginate()`" between
  unrelated subclasses.
- Subclasses that override most of the parent's methods.
- Three or more levels of inheritance, especially when the leaves disagree about the
  top's intent.
- Mixins multiplying to inject orthogonal behaviours.

### Redirects

1. **Composition.** "Has a logger" and "uses a validator" are has-a, not is-a. Inject the
   collaborator; call its methods.
2. **Delegation.** When you need "behaves-like-X for some calls, my-own-thing for
   others", delegate the X-calls to a held instance — see
   `fundamental/delegation_pattern.md`.
3. **Strategy / template instead of subclassing.** If subclasses only differ by one
   pluggable step, lift that step into a callable — see `behavioral/strategy.md`,
   `behavioral/template.md`.
4. **Mixins, last resort.** If you must use a mixin, keep it small and orthogonal:
   one focused capability per mixin, never overlapping with another mixin's MRO.

---

## How to flag and redirect in conversation

When the user types one of the trigger phrases, structure the reply like this:

1. **Acknowledge what they asked for** — do not dismiss it. "Yes, you can do this with a
   Singleton, but…"
2. **State the cost** in one sentence — the concrete pain (testability, hidden coupling,
   diff noise).
3. **Offer the redirect** with a short example using *their* code, not abstract names.
4. **Ask** before implementing. If they confirm the anti-pattern is what they want,
   implement it but leave a comment recording the trade-off so future-them remembers.

The point is not to refuse. The point is to make the cost legible.
