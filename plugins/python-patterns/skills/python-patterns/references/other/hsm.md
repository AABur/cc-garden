# Hierarchical State Machine (HSM)

**TL;DR:** A state machine where states are nested. A child state inherits its parent
state's transitions and behaviours, overriding only what is needed.

**Category:** Other (non-GoF)

## When to use

- A state machine has groups of states sharing common transitions
  (`OutOfService.Failed` and `OutOfService.Suspect` both react to `operator_inservice`
  identically).
- The flat state machine has explosion of redundant transitions.
- You want to model fallback semantics — child handles, otherwise parent handles.

## When NOT to use (Pythonic alternatives first)

- **Library FSMs.** `transitions` (in particular `transitions.extensions.HierarchicalMachine`)
  and `python-statemachine` give you HSM without rolling your own.
- **A flat state machine** is enough when groups have no shared behaviour.
- **A simple `state: Literal[...]` plus transition table** is enough when the state
  set is small and no nesting is required.

## Canonical implementation

From `faif/python-patterns` (`patterns/other/hsm/hsm.py`), abridged. Models a
telecom unit with nested states (`Active`, `Standby` ⊂ `Inservice`; `Suspect`,
`Failed` ⊂ `OutOfService`):

```python
class HierachicalStateMachine:
    def __init__(self):
        self._active_state = Active(self)
        self._standby_state = Standby(self)
        self._suspect_state = Suspect(self)
        self._failed_state = Failed(self)
        self._current_state = self._standby_state
        self.states = {
            "active":  self._active_state,
            "standby": self._standby_state,
            "suspect": self._suspect_state,
            "failed":  self._failed_state,
        }
        self.message_types = {
            "fault trigger":      self._current_state.on_fault_trigger,
            "switchover":         self._current_state.on_switchover,
            "diagnostics passed": self._current_state.on_diagnostics_passed,
            "diagnostics failed": self._current_state.on_diagnostics_failed,
            "operator inservice": self._current_state.on_operator_inservice,
        }

    def _next_state(self, state):
        try: self._current_state = self.states[state]
        except KeyError: raise UnsupportedState
```

Each concrete state class handles the messages it knows about; unhandled messages
delegate to the parent state's handler. The structure can be modelled either via
inheritance (parent state implements common transitions, child overrides) or via
delegation (each state holds a reference to its parent).

## Real-world examples

- **Telecom protocols** with redundant pairs (Active/Standby) and fault states
  (Suspect/Failed).
- **UI workflows** with nested modes (editing > modal-dialog > nested-dialog).
- **Game AI** with high-level modes ("patrolling") containing sub-states ("walking",
  "looking around").
- **Embedded device firmware** with operating regimes (Boot, Run, Sleep, Error) and
  sub-states inside each.

## Refactor recipe

When a flat state machine has many transitions duplicated across states:

1. Group states with shared behaviour into "super-states" (parent in the hierarchy).
2. Move shared transitions to the parent.
3. Each child handles only its specific differences; falls through to the parent
   otherwise.
4. If the resulting machinery is non-trivial, switch to a library.

## Review checklist

- Good: The hierarchy reflects domain reality, not a contrivance to share code.
- Good: Fall-through to parent is explicit — readers can trace which state handles which
  message.
- Good: Initial / default sub-state is documented for each parent state.
- Bad: The hierarchy nests too deeply; comprehensibility collapses past 2–3 levels.
- Bad: Hand-rolled HSM that duplicates a library's features. Use `transitions`.
- Bad: Mixed patterns — some transitions inherit, others duplicate; the contract is
  unclear.
