# Template Method

**TL;DR:** Define the skeleton of an algorithm in a base, deferring some steps to
subclasses (or pluggable callables). Subclasses fill in the variable steps without
changing the algorithm's overall shape.

**Category:** Behavioral

## When to use

- An algorithm has a fixed structure with a few customizable steps.
- Multiple variants share the structure but differ in specifics.
- You want to enforce the order/structure while letting users override individual
  steps.

## When NOT to use (Pythonic alternatives first)

- **Function with callable parameters.** Pass the variable steps as functions —
  Pythonic Template Method without subclassing.
- **Strategy.** If only *one* step varies, that is a Strategy
  (`behavioral/strategy.md`); a Template Method's value is enforcing a *sequence*
  of variable steps.
- **Class-based views** in Django are a domain-specific Template Method; if your
  framework already provides one, use it.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/template.py`) — the modern
Pythonic form uses callable parameters rather than subclassing:

```python
def get_text() -> str: return "plain-text"
def get_pdf()  -> str: return "pdf"
def get_csv()  -> str: return "csv"

def convert_to_text(data: str) -> str:
    print("[CONVERT]")
    return f"{data} as text"

def saver() -> None: print("[SAVE]")

def template_function(getter, converter=False, to_save=False) -> None:
    data = getter()
    print(f"Got `{data}`")
    if len(data) <= 3 and converter:
        data = converter(data)
    else:
        print("Skip conversion")
    if to_save:
        saver()
    print(f"`{data}` was processed")

template_function(get_pdf, converter=convert_to_text)
# Got `pdf`
# [CONVERT]
# `pdf as text` was processed
```

The "template" is the function `template_function`; the variable steps are the
`getter`, `converter`, and the optional `saver`. Subclassing is only needed when the
steps share state.

## Real-world examples

- **Django class-based views** — `dispatch()` is the template; subclasses fill
  `get()`, `post()`, etc. (cited upstream).
- **`unittest.TestCase`** — `setUp` / `tearDown` / `test_*` is a template
  algorithm.
- **`logging.Logger.handle`** — fixed flow with overridable filtering hooks.
- **`csv.DictWriter`** — `writeheader` / `writerow` shape with hookable serialization.

## Refactor recipe

When the same 5-step algorithm is copy-pasted with one or two variations across
classes:

1. Extract the common steps into a base class method or a free function.
2. Identify the variable steps; make them either abstract methods or callable
   parameters.
3. The fixed portion of the algorithm lives in the base / function; subclasses or
   callers supply the missing pieces.
4. Tests can exercise the template with mocked steps.

## Review checklist

- ✅ The fixed portion of the algorithm cannot be skipped or reordered by mistake.
- ✅ Variable steps are clearly documented (name, signature, contract).
- ✅ When a step is genuinely optional, the template handles its absence gracefully.
- ❌ Subclasses override the *fixed* part of the template, breaking the structure.
  Make those parts truly fixed (final, not overridable).
- ❌ The template has accumulated optional knobs to the point that no two callers
  use the same flow. Split into multiple templates.
- ❌ A function with callable args was simpler; the class hierarchy is over-engineered.
