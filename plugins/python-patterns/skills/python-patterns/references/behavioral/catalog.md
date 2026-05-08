# Catalog

**TL;DR:** Use a constructor parameter to select which method (from a fixed catalog of
specialized methods) the main entry point will execute.

**Category:** Behavioral

## When to use

- A class has a fixed family of behaviours and clients pick one at construction time.
- You want a clean switch on the parameter without `if/elif` cascades inside the method
  body.
- The dispatch is *closed* — the catalog is fixed by the class author.

## When NOT to use (Pythonic alternatives first)

- **`dict[str, Callable]`** at module level. If the catalog does not need to be tied
  to a class, just dispatch through a dict.
- **Subclassing.** If you want users to *extend* the catalog, that is `Strategy`
  (`behavioral/strategy.md`) or `Registry` (`behavioral/registry.md`).
- **`functools.singledispatch`** for dispatch on argument *type* rather than a string
  parameter.
- **`match` statement (3.10+)** when the dispatch is local to one site.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/catalog.py`), abridged. Several
flavours co-exist (static, instance, class methods); the static-method flavour is the
typical one:

```python
class Catalog:
    def __init__(self, param: str) -> None:
        self._choices = {
            "param_value_1": self._method_1,
            "param_value_2": self._method_2,
        }
        if param not in self._choices:
            raise ValueError(f"Invalid param: {param}")
        self.param = param

    @staticmethod
    def _method_1() -> str: return "executed method 1!"
    @staticmethod
    def _method_2() -> str: return "executed method 2!"

    def main_method(self) -> str:
        return self._choices[self.param]()
```

`main_method()` is the single public entry. Behaviour is selected once at
construction; calls thereafter dispatch through the dict.

## Real-world examples

- **Web frameworks** mapping HTTP methods to handlers via dispatch dicts.
- **Argparse subparsers** select handler based on subcommand string.
- **Factory function variants** in libraries like `tkinter` where one constructor
  branches on a parameter.

## Refactor recipe

When a method body is one big `if param == "x": ... elif param == "y": ...`:

1. Extract each branch into its own (static / class / instance) method.
2. Build a dispatch dict mapping the parameter to the method.
3. Validate the parameter once at construction.
4. The public method becomes a single dict lookup + call.

## Review checklist

- ✅ Parameter is validated once; subsequent calls do not re-validate.
- ✅ Each branch becomes one focused method, easy to read in isolation.
- ✅ The catalog is documented (which params are valid? which method does each map to?).
- ❌ The dispatch dict and the methods drift — params with no matching method, or
  methods not reachable from any param.
- ❌ The "catalog" has only two entries and the `if/else` was already clear; this is
  ceremony.
- ❌ The dict references unbound methods that need awkward `__get__` ceremony to call;
  prefer staticmethods or module-level functions to keep call sites simple.
