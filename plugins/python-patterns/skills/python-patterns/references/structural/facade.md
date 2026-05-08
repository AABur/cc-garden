# Facade

**TL;DR:** Provide a single, simpler interface in front of a complex subsystem.

**Category:** Structural

## When to use

- A subsystem has a wide surface, and most clients only need a small slice.
- You want to hide initialization order, lifecycle, or wiring details.
- You are integrating a complex library and want a curated entry point your team
  uses.

## When NOT to use (Pythonic alternatives first)

- **A function suffices.** If the "facade" is one function calling three things,
  it is just a function — give it a good name and be done.
- **The subsystem is already simple.** Adding a facade because "all systems should
  have facades" is ceremony.
- **You really wanted Adapter.** Facade simplifies; Adapter translates. If the
  underlying interface is *fine* but mismatched to a consumer's expected shape, see
  `structural/adapter.md`.
- **Generic wrapper class around a single object.** That is a wrapper, not a facade.
  Facade gathers *several* moving parts behind one API.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/facade.py`), abridged:

```python
class CPU:
    def freeze(self): print("Freezing")
    def jump(self, p): print(f"Jump {p}")
    def execute(self): print("Execute")

class Memory:
    def load(self, p, d): print(f"Load {p} {d}")

class SolidStateDrive:
    def read(self, lba, size): return f"data@{lba}[{size}]"

class ComputerFacade:
    def __init__(self):
        self.cpu = CPU()
        self.memory = Memory()
        self.ssd = SolidStateDrive()

    def start(self):
        self.cpu.freeze()
        self.memory.load("0x00", self.ssd.read("100", "1024"))
        self.cpu.jump("0x00")
        self.cpu.execute()
```

`ComputerFacade.start()` collapses a multi-step subsystem startup into one method.
Clients call `start()`; the orchestration is hidden.

## Real-world examples

- **`os.path.isdir(path)`** is a facade over `stat()` machinery (cited in upstream
  docstring).
- **`requests.get(url)`** is a facade over `urllib3` connection pooling, retries,
  cookies, and session state.
- **`subprocess.run()`** is a facade over `Popen` wiring.
- **Application startup modules** that wire up loggers, databases, queues, and metrics
  in one `init_app()` call.

## Refactor recipe

When clients of a subsystem repeat the same 5-step init dance:

1. Identify the common usage pattern across call sites.
2. Define a facade class or function that performs the dance and exposes the few
   methods clients actually need.
3. Migrate call sites to the facade, leaving the underlying API available for advanced
   users.
4. Document which facade methods cover which use cases; flag escape hatches to the
   underlying API.

## Review checklist

- ✅ The facade is *thin* — it orchestrates, it does not re-implement subsystem logic.
- ✅ Advanced users can still bypass the facade for capabilities it does not expose.
- ✅ Facade methods are named for the *use case*, not the underlying mechanics.
- ❌ The facade has accumulated business logic that belongs in the subsystem or in
  callers.
- ❌ The facade shadows nearly every method of the subsystem — if it is mostly
  pass-through, it is not adding value.
- ❌ Multiple facades over the same subsystem, with overlapping responsibilities.
  Consolidate.
