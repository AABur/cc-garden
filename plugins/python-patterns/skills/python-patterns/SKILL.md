---
name: python-patterns
description: >-
  Use this skill for Python design problems where a GoF or Python-specific
  design pattern is the right tool — picking the pattern, refactoring naive
  code into it, or reviewing existing code for pattern misuse.

  Trigger when the user (a) names a pattern by name on Python code: Factory,
  Strategy, Observer, Builder, Singleton, Adapter, Decorator, Proxy, Visitor,
  Command, Chain of Responsibility, State, Template Method, Memento, Iterator,
  Mediator, Composite, Bridge, Facade, Flyweight, Abstract Factory, Borg,
  Prototype, Pool, Publish-Subscribe, Registry, Specification, Dependency
  Injection, MVC, "GoF"; (b) describes a Python design symptom that maps to
  one — long isinstance / elif dispatch chains, an object with many optional
  constructor fields, undo / redo, stateful workflows, event hooks for
  subscribers, every subclass copying the same skeleton with one tweak,
  parallel class hierarchies, wrapping a service to add logging or auth,
  "this class is huge", "this looks over-engineered", "is this Pythonic?";
  (c) asks for a Python design / code review or refactor of OOP code.

  Also trigger when the user is about to introduce a Singleton, God Object,
  or deep inheritance hierarchy in Python — flag the anti-pattern and propose
  the Pythonic alternative (module globals, Borg, composition, delegation).

  Skip: pandas / numpy data analysis, framework-specific routing or ORM
  (Django views, FastAPI dependencies, SQLAlchemy sessions), one-shot scripts,
  non-OOP functional code, library version / config / install questions.
---

# python-patterns — pattern selection, refactoring, and review for Python

You apply the catalog of design patterns from
[faif/python-patterns](https://github.com/faif/python-patterns) to Python source. The
catalog is loaded **lazily**: read only the reference files relevant to the current task.

## Core principle: WHY before HOW

The upstream README puts it precisely:

> *"Each pattern has its own trade-offs. Pay attention more to **why** you're choosing
> a certain pattern than to **how** to implement it."*

Three commitments follow:

1. **Pythonic first.** Plain Python — first-class functions, `dataclass`, generators,
   `@decorator` syntax, modules-as-singletons, dispatch dicts — usually beats classical
   GoF. Reach for a pattern only when the abstraction genuinely earns its complexity.
2. **Anti-pattern guard.** Singleton, God Object, and inheritance overuse are flagged and
   redirected. They are not implemented even on direct request without the user being
   shown the alternative.
3. **No gratuitous ceremony.** Adding a class hierarchy where a function suffices is
   harm, not help. When code review surfaces a "pattern", first ask whether the pattern
   is doing real work.

## Workflow

Decide what the user wants, then route:

```
intent? ───────────────────────────────────────────────────────────────
  │
  ├── new code        → "what's the right shape?"
  ├── refactor        → "what's wrong with the current shape?"
  └── review          → "what should the reviewer flag?"

then in all three cases:
  │
  ├── Step 1: anti-pattern check
  │   if user asks for Singleton / God Object / massive inheritance
  │   → read references/anti-patterns.md, redirect, do not implement.
  │
  ├── Step 2: Pythonic check
  │   if the problem is solved by plain Python (functions, dataclass,
  │   generator, @decorator, dict dispatch)
  │   → read references/pythonic-alternatives.md, recommend that.
  │
  ├── Step 3: pattern selection
  │   map the problem description to a pattern via the lookup table below
  │   or references/selection-guide.md
  │   → read references/<category>/<pattern>.md
  │   → apply with full context (when to use, when not, refactor recipe,
  │     review checklist).
  │
  └── Step 4: present the trade-off
      always show the user *why* the chosen pattern fits this problem and
      what the cheaper alternative would have been. Even when the pattern
      is correct, the user benefits from seeing the alternative ruled out.
```

## Quick lookup table

Common phrasings the user might use → reference file to read.

| If the user says (or the code shows)…                                      | Read                                                           |
|----------------------------------------------------------------------------|----------------------------------------------------------------|
| "different algorithms for the same task" / sort by N criteria              | `behavioral/strategy.md` (and check `pythonic-alternatives.md`)|
| "construct object with 10+ params" / many constructor variants             | `creational/builder.md` (compare `dataclass`)                  |
| "I need a Singleton" / "one instance of X"                                 | `anti-patterns.md` first, then `creational/borg.md`            |
| "decouple a subsystem behind one API" / "complicated startup"              | `structural/facade.md`                                         |
| "notify subscribers when X changes"                                        | `behavioral/observer.md`, `behavioral/publish_subscribe.md`    |
| "undo / redo / queue commands"                                             | `behavioral/command.md` (+ `memento.md` for state)             |
| "lots of `if isinstance(x, …)` chains"                                     | `behavioral/strategy.md` or `behavioral/visitor.md`            |
| "state machine with transitions"                                           | `behavioral/state.md` (or `other/hsm.md` for hierarchical)     |
| "all subclasses repeat the same skeleton"                                  | `behavioral/template.md`                                       |
| "tree of nodes, leaves and groups treated alike"                           | `structural/composite.md`                                      |
| "wrap object with extra behaviour"                                         | `structural/decorator.md` (+ Python `@decorator` syntax)       |
| "adapt third-party class to my interface"                                  | `structural/adapter.md`                                        |
| "lazy / cached property"                                                   | `creational/lazy_evaluation.md`                                |
| "shared state across instances"                                            | `creational/borg.md`                                           |
| "expensive object reuse / connection pool"                                 | `creational/pool.md`                                           |
| "clone an object"                                                          | `creational/prototype.md`                                      |
| "select handler from string / dispatch table"                              | `behavioral/catalog.md` or `behavioral/registry.md`            |
| "pipeline of handlers, first capable wins"                                 | `behavioral/chain_of_responsibility.md`                        |
| "fluent API / method chaining"                                             | `behavioral/chaining_method.md`                                |
| "many objects, lots of duplicated state"                                   | `structural/flyweight.md`                                      |
| "swap remote object for local proxy / lazy loading"                        | `structural/proxy.md`                                          |
| "compose object hierarchies with their own configuration trees"            | `structural/bridge.md`                                         |
| "single entry point for incoming web requests"                             | `structural/front_controller.md`                               |
| "data ↔ business logic ↔ presentation"                                     | `structural/3-tier.md`, `structural/mvc.md`                    |
| "business rules combined with AND / OR / NOT"                              | `behavioral/specification.md`                                  |
| "iterate a custom container"                                               | `behavioral/iterator.md` (often a generator beats this)        |
| "mediator between many tightly-coupled objects"                            | `behavioral/mediator.md`                                       |
| "snapshot / restore previous state"                                        | `behavioral/memento.md`                                        |
| "common helpers without inheritance"                                       | `behavioral/servant.md` or `fundamental/delegation_pattern.md` |
| "wire dependencies for tests" / "swap real DB for fake"                    | `testability/dependency_injection.md`                          |
| "shared blackboard solved by independent agents"                           | `other/blackboard.md`                                          |
| "graph traversal / shortest path"                                          | `other/graph_search.md`                                        |

If the table does not match, fall back to `references/selection-guide.md` for a more
discursive problem-first index.

## Anti-pattern triggers (read first)

Whenever the user says any of these, **read `references/anti-patterns.md` before doing
anything else**:

- "Singleton", "make it a singleton", "ensure only one instance"
- "God class", "manager that does everything", "single class that holds the world"
- "make X inherit from this big base class", deep inheritance trees, "extend FrameworkThing"
- "global state for…", "globally accessible config object"

The skill does not silently implement these. It flags them, explains why they are an
issue in Python specifically, and proposes the Pythonic redirect (typically a module-level
value, a Borg, composition, or dependency injection).

## Reference index

### Creational (`references/creational/`)
| File | Intent |
| --- | --- |
| `abstract_factory.md` | Generic function with specific factories. |
| `borg.md` | Singleton-with-shared-state alternative for "one logical state, many instances". |
| `builder.md` | Build complex objects step-by-step instead of via N constructors. |
| `factory.md` | Delegate instance creation to a function/method. |
| `lazy_evaluation.md` | Lazily-evaluated property. |
| `pool.md` | Pre-instantiate and recycle expensive objects. |
| `prototype.md` | Clone an existing object instead of constructing. |

### Structural (`references/structural/`)
| File | Intent |
| --- | --- |
| `3-tier.md` | Strict data ↔ business logic ↔ presentation separation. |
| `adapter.md` | Make one interface look like another. |
| `bridge.md` | Decouple abstraction from implementation; vary independently. |
| `composite.md` | Treat individual and composite objects uniformly. |
| `decorator.md` | Wrap functionality around an object. |
| `facade.md` | One simpler API hiding a complex subsystem. |
| `flyweight.md` | Share intrinsic state across many small objects. |
| `front_controller.md` | Single handler routing all incoming requests. |
| `mvc.md` | Loose model ↔ view ↔ controller separation. |
| `proxy.md` | Stand-in that controls access to a real subject. |

### Behavioral (`references/behavioral/`)
| File | Intent |
| --- | --- |
| `catalog.md` | Dispatch among specialized methods by construction parameter. |
| `chain_of_responsibility.md` | Pass a request along a handler chain until handled. |
| `chaining_method.md` | Fluent API where each call returns `self`. |
| `command.md` | Bundle a request as an object so it can be queued, undone, logged. |
| `iterator.md` | Sequential access to a container's elements. |
| `mediator.md` | Centralize complex peer-to-peer communication. |
| `memento.md` | Capture and restore an object's internal state. |
| `observer.md` | Notify dependents on state change. |
| `publish_subscribe.md` | Broker decouples publishers from many subscribers. |
| `registry.md` | Track all subclasses or instances of a type. |
| `servant.md` | Provide common functionality without inheritance. |
| `specification.md` | Combine business rules with boolean logic. |
| `state.md` | Object behaviour changes with internal state. |
| `strategy.md` | Pluggable, interchangeable algorithms. |
| `template.md` | Skeleton with overridable hook steps. |
| `visitor.md` | Add operations to a structure without modifying it. |

### Testability (`references/testability/`)
| File | Intent |
| --- | --- |
| `dependency_injection.md` | Inject collaborators so tests can swap them. |

### Fundamental (`references/fundamental/`)
| File | Intent |
| --- | --- |
| `delegation_pattern.md` | An object handles a request by forwarding to a delegate. |

### Other / non-GoF (`references/other/`)
| File | Intent |
| --- | --- |
| `blackboard.md` | Independent specialists collaborate on a shared workspace. |
| `graph_search.md` | Graph traversal (DFS/BFS, shortest path). |
| `hsm.md` | Hierarchical state machine — states-within-states. |

### Cross-cutting (`references/`)
| File | Purpose |
| --- | --- |
| `selection-guide.md` | Problem-first lookup, broader than the table above. |
| `pythonic-alternatives.md` | When plain Python beats the classical pattern. |
| `anti-patterns.md` | Singleton, God Object, inheritance overuse — flag and redirect. |

## Compact review checklist

When reviewing Python code through this skill's lens, run through these eight heuristics
once. Each maps to a reference file you can pull in for the deep version.

1. **Singleton sighting.** Any class with `_instance` / `__new__` games?
   → `anti-patterns.md` (use module global or Borg).
2. **God Object.** A class with > 7–10 responsibilities?
   → `anti-patterns.md` (split by responsibility; prefer composition).
3. **Deep inheritance.** Base classes more than two levels deep, or used to share helpers
   rather than to model an "is-a"?
   → `anti-patterns.md` + `fundamental/delegation_pattern.md` (use composition or
   delegation).
4. **`if isinstance(...)` chains.** A switch on type, hand-rolled?
   → `behavioral/strategy.md` (functions or dataclasses) or `behavioral/visitor.md`.
5. **Hand-rolled decorator class.** Wrapping with a class instead of `@decorator`?
   → `structural/decorator.md` + `pythonic-alternatives.md`.
6. **Hand-rolled iterator.** `__init__` + `__next__` book-keeping for a sequential walk?
   → `behavioral/iterator.md` (a generator usually wins).
7. **Constructor with N optional params, all defaulted.** Telescoping constructor?
   → `creational/builder.md` *or* `dataclass(field=…)` first.
8. **Global mutable state.** Module-level dicts, lists, flags accumulating writes?
   → `testability/dependency_injection.md` (inject; tests will thank you).

## Output style

When you suggest a pattern:

- State the problem in the user's words first ("you have N variants of …").
- Name the chosen pattern *and* the runner-up (the Pythonic alternative or the next
  pattern). Tell the user why the chosen one fits.
- Show a minimal working sketch grounded in the user's code, not the canonical example
  from the reference (the canonical example is for *you*, not the user).
- For refactors, present a **step-by-step recipe** the user can apply incrementally
  without breaking tests at each step.
- For reviews, lead with the highest-confidence finding. Mark each finding's confidence
  ("certain" / "likely" / "speculative") so the user can weigh them.
