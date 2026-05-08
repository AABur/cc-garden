# Command

**TL;DR:** Encapsulate a request as an object, so it can be parameterized, queued,
logged, undone, or shipped across processes.

**Category:** Behavioral

## When to use

- You need *undo* — each command knows how to invert itself.
- Requests must be *queued* or *scheduled* — turning them into objects lets a queue
  hold heterogeneous work.
- Requests must be *logged* or *replayed* — serializable command objects support audit
  and time-travel.
- The invoker (button, menu item, hotkey) is decoupled from the receiver (file
  system, database).

## When NOT to use (Pythonic alternatives first)

- **`functools.partial(fn, *args)`** captures a callable plus arguments. For "call
  later" without undo or logging, this is the answer.
- **A closure** captures the same thing more flexibly.
- **A list of `(callable, args, kwargs)` tuples** is a queue.
- **Plain function calls.** If you do not need the metadata (undo, queue, log),
  the Command class is ceremony.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/command.py`), abridged:

```python
class HideFileCommand:
    def __init__(self):
        self._hidden_files: list[str] = []
    def execute(self, filename: str) -> None:
        print(f"hiding {filename}")
        self._hidden_files.append(filename)
    def undo(self) -> None:
        filename = self._hidden_files.pop()
        print(f"un-hiding {filename}")

class DeleteFileCommand:
    def __init__(self): self._deleted: list[str] = []
    def execute(self, filename: str) -> None:
        print(f"deleting {filename}")
        self._deleted.append(filename)
    def undo(self) -> None:
        filename = self._deleted.pop()
        print(f"restoring {filename}")

class MenuItem:
    def __init__(self, command):
        self._command = command
    def on_do_press(self, filename: str): self._command.execute(filename)
    def on_undo_press(self):              self._command.undo()
```

Commands hold their own undo state. The `MenuItem` (invoker) does not know which
command it holds.

## Real-world examples

- **Editor undo/redo stacks.** Each user action is a Command pushed onto an undo
  stack.
- **Database transactions** as conceptual commands with rollback.
- **Job queues** like Celery, RQ — each task is a serializable command shipped to a
  worker.
- **`argparse` actions** — custom action classes are Command-shaped.

## Refactor recipe

When you have multiple "do X" buttons each with custom code, and want to add undo:

1. Define a Command interface (`execute` and `undo`).
2. Wrap each action as a Command class capturing the data it needs.
3. The button (invoker) only calls `command.execute()` / `command.undo()`.
4. Maintain an undo stack — push each executed command, pop on undo.
5. For redo, keep a parallel stack.

## Review checklist

- Good: `execute` and `undo` are inverse — applying both leaves the state unchanged.
- Good: Commands capture all data they need; no implicit dependence on global state.
- Good: Undo stack is bounded or pruned to avoid unbounded memory.
- Bad: Commands mutate global state in ways `undo` does not capture; undo is incomplete.
- Bad: Commands without undo logic, used purely for queueing — `functools.partial` is
  shorter.
- Bad: Commands that "do everything"; per the upstream docs, the value of Command is
  exactly that each is one focused action.
