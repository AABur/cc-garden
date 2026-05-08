# State

**TL;DR:** An object's behaviour changes when its internal state changes, as if it had
changed class. Each state is its own class with its own behaviours; transitions move
the object from one to another.

**Category:** Behavioral

## When to use

- The object has a small set of *qualitatively different* states, each with its own
  behaviour for the same operations (Radio in `AM` vs `FM` mode; TCP connection in
  `LISTEN` vs `ESTABLISHED`).
- Transitions follow a finite-state-machine logic.
- The state-specific behaviour is more than a couple of `if`s — extracting per-state
  classes pays off.

## When NOT to use (Pythonic alternatives first)

- **`state: Literal["a", "b", "c"]`** plus a transition table is enough for many
  cases. A class per state is justified when each state encapsulates non-trivial
  behaviour.
- **Library-supported FSM** (`transitions`, `python-statemachine`) — they handle
  history, transitions, and validation cleanly.
- **A Strategy pattern (`behavioral/strategy.md`)** if the choice of behaviour is not
  about *transitioning* but just about plugging in a variant.
- **Hierarchical states** — see `other/hsm.md`.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/state.py`), abridged:

```python
from __future__ import annotations

class State:
    def scan(self) -> None:
        self.pos = (self.pos + 1) % len(self.stations)
        print(f"Scanning... Station is {self.stations[self.pos]} {self.name}")

class AmState(State):
    def __init__(self, radio: Radio):
        self.radio, self.stations, self.pos, self.name = radio, ["1250","1380","1510"], 0, "AM"
    def toggle_amfm(self):
        print("Switching to FM"); self.radio.state = self.radio.fmstate

class FmState(State):
    def __init__(self, radio: Radio):
        self.radio, self.stations, self.pos, self.name = radio, ["81.3","89.1","103.9"], 0, "FM"
    def toggle_amfm(self):
        print("Switching to AM"); self.radio.state = self.radio.amstate

class Radio:
    def __init__(self):
        self.amstate = AmState(self)
        self.fmstate = FmState(self)
        self.state = self.amstate
    def toggle_amfm(self): self.state.toggle_amfm()
    def scan(self):        self.state.scan()
```

The `Radio` delegates every operation to its current state. The state holds the
behaviour and decides the next state.

## Real-world examples

- **`transitions` library** — explicit Python FSM library with hooks, callbacks,
  history.
- **`asyncio` task / future states** (PENDING, RUNNING, DONE, CANCELLED).
- **TCP connection state machines** in network code.
- **Order workflows** in e-commerce (CART, PENDING, PAID, SHIPPED, DELIVERED).
- **Game character states** (idle, running, jumping, dead).

## Refactor recipe

When a class has methods that all start with `if self.mode == "x": ... elif ...`:

1. Identify the discrete modes/states.
2. Create a class per state with the methods that vary.
3. Delegate the original class's methods to the current state.
4. Implement transitions inside state classes; they assign the next state on the
   context object.
5. Consider a library if states are many or transitions complex.

## Review checklist

- ✅ Each state class has the same set of methods (uniform interface) so the context
  can delegate uniformly.
- ✅ Transitions are explicit; you can list which transitions are legal.
- ✅ Invalid transitions raise rather than silently no-op.
- ❌ The state classes have grown to be tightly coupled with the context's privates.
  Push behaviour into the state, expose narrow accessors on the context.
- ❌ States proliferate beyond the domain reality — collapse merged states.
- ❌ A library FSM was a better fit; the hand-rolled version is missing transition
  guards, hooks, persistence.
