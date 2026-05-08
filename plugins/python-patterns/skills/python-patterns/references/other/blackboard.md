# Blackboard

**TL;DR:** Multiple specialized "experts" (knowledge sources) collaborate via a
shared workspace (the blackboard); a controller picks which expert acts next based on
the current state of the blackboard.

**Category:** Other (non-GoF, AI/architectural)

## When to use

- Problems with no single algorithmic path to the answer; partial solutions
  accumulate from heterogeneous specialists.
- Speech recognition, computer vision, scheduling — historically the home of this
  pattern.
- Modern incarnations: multi-agent LLM systems where the blackboard is shared scratch
  state and "experts" are specialized agents.

## When NOT to use (Pythonic alternatives first)

- **A pipeline.** If the order of steps is fixed and known, a linear pipeline beats
  a blackboard.
- **An event bus.** If specialists are reactive and stateless, pub-sub
  (`behavioral/publish_subscribe.md`) is simpler.
- **Workflow engine.** Airflow, Prefect, Temporal — domain-specific orchestrators
  for production work.

## Canonical implementation

From `faif/python-patterns` (`patterns/other/blackboard.py`), abridged:

```python
from abc import ABC, abstractmethod

class AbstractExpert(ABC):
    def __init__(self, blackboard): self.blackboard = blackboard

    @property
    @abstractmethod
    def is_eager_to_contribute(self) -> bool: ...

    @abstractmethod
    def contribute(self) -> None: ...

class Blackboard:
    def __init__(self):
        self.experts: list = []
        self.common_state = {"problems": 0, "suggestions": 0,
                             "contributions": [], "progress": 0}
    def add_expert(self, expert): self.experts.append(expert)

class Controller:
    def __init__(self, blackboard): self.blackboard = blackboard
    def run_loop(self):
        while self.blackboard.common_state["progress"] < 100:
            for expert in self.blackboard.experts:
                if expert.is_eager_to_contribute:
                    expert.contribute()
        return self.blackboard.common_state["contributions"]

class Student(AbstractExpert):
    @property
    def is_eager_to_contribute(self) -> bool: return True
    def contribute(self) -> None:
        self.blackboard.common_state["progress"] += 1
        ...
```

Each expert reads the blackboard, decides whether to act, and writes results back.
The controller drives the loop until done.

## Real-world examples

- **Speech recognition (HEARSAY-II)** — original Blackboard system.
- **Hybrid AI / expert systems** combining symbolic and statistical reasoning.
- **Multi-agent LLM scratchpads** — modern workflows where multiple LLM "experts"
  read and write to a shared state until the goal is reached.

## Refactor recipe

When you have a problem with no clear linear solution and several specialized
modules contribute partial answers:

1. Define the shared state — what does every expert read and write?
2. Create an `Expert` interface with `is_eager_to_contribute` (or equivalent
   priority) and `contribute`.
3. Implement each specialist as a class.
4. Build a controller loop that selects and runs experts until done.
5. Add termination guards — without them the loop can be infinite.

## Review checklist

- ✅ The shared state is well-defined; experts agree on its schema.
- ✅ Termination is guaranteed — `progress` reaches 100 (or a maximum iteration count
  is enforced).
- ✅ Concurrency (if any) is bounded; experts do not race on shared state without
  protection.
- ❌ The blackboard has accumulated unrelated state. Split or modularize.
- ❌ Order of expert contribution is critical but not enforced; a pipeline would have
  been clearer.
- ❌ Used where a workflow engine or pub-sub is the better fit; ceremony for a simple
  problem.
