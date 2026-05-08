# Selection guide — problem first, pattern second

Use this when the SKILL.md lookup table does not match the user's phrasing exactly. The
sections below are organized by *the problem the user is trying to solve*, not by the
pattern's name.

For each problem you will see:
- The minimal description of the problem.
- The Pythonic answer to consider first.
- The classical pattern(s) and when each is preferable.

---

## "I have several variants of an algorithm and want to swap them at runtime"

**Pythonic first:** assign a function to a variable; build a `dict[str, Callable]`
table.

**Classical:** `behavioral/strategy.md`. Pick this when variants carry persistent
internal state, or when shared boilerplate justifies a base class.

Adjacent: `behavioral/template.md` if the variants share a *skeleton* and only differ
in a few overridable steps.

---

## "Construction has too many parameters / too many constructor variants"

**Pythonic first:** `dataclass` with keyword-only fields, sensible defaults, factories
(`field(default_factory=...)`), and `pydantic` if validation matters.

**Classical:** `creational/builder.md`. Pick this when construction has stages with
intermediate validity, or when the final type depends on choices made during
construction.

Adjacent: `creational/factory.md` for "function returns instance, picks subclass by
input"; `creational/abstract_factory.md` if you need *families* of related products.

---

## "I want exactly one of something across the program"

**Pythonic first:** module-level value. See `anti-patterns.md`.

**Classical alternative if you really need shared state across many instances:**
`creational/borg.md` (Borg, Monostate). Different instances, same `__dict__`.

**Anti-pattern, do not implement silently:** Singleton. Read `anti-patterns.md`.

---

## "I want to expose a simple API in front of a complex subsystem"

**Pythonic first:** a function or small module that calls into the subsystem. Often
"facade" emerges naturally without the pattern label.

**Classical:** `structural/facade.md`. Pick when the subsystem's surface is genuinely
broad and the facade meaningfully reduces what callers must learn.

Adjacent: `structural/front_controller.md` for *web requests* specifically.

---

## "I want listeners to react when something changes"

**Pythonic first:** a list of callables; `for cb in callbacks: cb(event)`.

**Classical:**
- `behavioral/observer.md` — direct attach/detach by the subject.
- `behavioral/publish_subscribe.md` — broker decouples publishers from subscribers,
  better when many independent producers/consumers exist.

Adjacent: framework-native solutions (Django Signals, Flask Blinker) — point to those
if the project is using the framework.

---

## "I have a long `if isinstance(x, T): … elif isinstance(x, U): …` chain"

**Pythonic first:** dispatch dict keyed on `type(x)`; or `functools.singledispatch`.

**Classical:**
- `behavioral/strategy.md` — if the chain is "pick algorithm based on type".
- `behavioral/visitor.md` — if you need to add operations to a fixed type hierarchy
  without modifying its classes.

Adjacent: `match` statement (Python 3.10+) is structural pattern matching at the
language level — often the right answer for "match shape and act".

---

## "I want to model state transitions"

**Pythonic first:** an explicit `state: Literal["a", "b", "c"]` plus a transition table
(`dict[(state, event), next_state]`).

**Classical:**
- `behavioral/state.md` — class-per-state, transitions in methods. Pick when each
  state has its own behaviour worth encapsulating.
- `other/hsm.md` — hierarchical state machine. Pick when states nest (parent-state
  default behaviour + child-state overrides).

---

## "I have part-whole hierarchies (folder/file, group/leaf)"

**Pythonic first:** rely on duck typing — both leaves and groups expose the same
methods.

**Classical:** `structural/composite.md`. Pick when you want a clean type definition,
and when "leaf is a degenerate composite" simplifies traversal logic.

---

## "I want to wrap an object with extra behaviour"

**Pythonic first:** `@decorator` for callables; `__getattr__` delegation for objects.
See `pythonic-alternatives.md`.

**Classical:** `structural/decorator.md`. Pick for non-callable wrapping where the
wrapper has its own state or interface (e.g., a file-like wrapper that adds
compression).

Adjacent: `structural/proxy.md` for "stand-in that controls access" rather than
"wrapper that adds capability". Decorators add; proxies gate.

---

## "I want to adapt one interface to another"

**Pythonic first:** a thin function or class that translates calls.

**Classical:** `structural/adapter.md`. Same idea, with the discipline of explicit
contract documentation. Pick when the adaptation is non-trivial enough to deserve a
named class.

---

## "I want undo / redo / queue commands / log all actions"

**Pythonic first:** `functools.partial` for "call later"; a list of `(action, args)`
tuples for a queue.

**Classical:** `behavioral/command.md`. Pick when you also need *undo* (each command
knows how to invert itself), serialization (commands persist to disk), or a
heterogeneous queue of differently-shaped requests.

Adjacent: `behavioral/memento.md` for snapshot-based undo (capture state, restore
state) instead of inverse-action undo.

---

## "I want to traverse a custom container"

**Pythonic first:** a generator function. `def __iter__(self): yield from ...`.

**Classical:** `behavioral/iterator.md`. Pick only when the iteration needs explicit
state visible to callers (peek, fork, reset), which a generator's local scope hides.

---

## "I want subscribers, plugins, or handlers to register themselves at import time"

**Classical:** `behavioral/registry.md`. Often combined with class decorators or
`__init_subclass__` for automatic registration.

Adjacent: `behavioral/catalog.md` for "select method based on construction param" — a
narrower registry use.

---

## "I have business rules I want to combine with AND/OR/NOT"

**Pythonic first:** plain boolean expressions on functions returning bool.

**Classical:** `behavioral/specification.md`. Pick when rules are *first-class* —
stored, combined, persisted, or composed at runtime.

---

## "Many similar objects share intrinsic state, memory is tight"

**Classical:** `structural/flyweight.md`. Niche; only invoke when memory pressure is
real.

---

## "I want to clone an object as the basis for a new one"

**Pythonic first:** `copy.deepcopy(obj)` or a `@dataclass`'s `replace()`.

**Classical:** `creational/prototype.md`. Pick when prototypes need to live in a
registry indexed by name (like preset configurations), and clients clone by name.

---

## "I need to manage a pool of expensive resources"

**Classical:** `creational/pool.md`. Database connections, threads, sockets — the
domain naturally fits.

Adjacent: stdlib `concurrent.futures.ThreadPoolExecutor` / `multiprocessing.Pool`
already implement this for execution; do not reinvent.

---

## "I want to inject dependencies for testability"

**Classical:** `testability/dependency_injection.md`. The pattern explanation in this
catalog is short and Python-specific (constructor injection, parameter injection,
attribute injection — no framework needed in most cases).

---

## "Code review found something but I am not sure it is a pattern issue"

Run the SKILL.md "Compact review checklist" — eight common smells, each pointing at
the relevant reference file. The smells are: Singleton, God Object, deep inheritance,
isinstance chains, hand-rolled decorator class, hand-rolled iterator, telescoping
constructor, global mutable state.

If none of those fit, it is probably a domain-modelling issue, not a pattern issue.
The catalog will not help; honest is better than reaching for a label.

---

## When no pattern fits

The most important skill is knowing when to leave well enough alone. If the code is
short, clear, tested, and unlikely to grow, *no pattern* is the right answer. The
catalog exists for code that is — or is about to become — non-trivial. Imposing a
pattern on simple code is a failure mode.
