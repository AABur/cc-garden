# Front Controller

**TL;DR:** A single component is the entry point for all incoming requests, then
dispatches to the right handler.

**Category:** Structural (architectural)

## When to use

- Web applications where every request goes through one controller for shared concerns
  (auth, logging, request parsing, error handling).
- Command-line dispatchers (`tool subcommand args`) — one router maps to many
  subcommand handlers.
- Plugin systems with a common entry handshake before delegating.

## When NOT to use (Pythonic alternatives first)

- **Your web framework already does this.** Django, Flask, FastAPI, Starlette — every
  Python web framework ships its own front controller. Do not reinvent.
- **Direct routing is enough.** If subcommand → function dispatch is a flat dict, you
  do not need a controller class.
- **Click / Typer / argparse** for CLI dispatch.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/front_controller.py`), abridged:

```python
class MobileView:
    def show_index_page(self): print("Mobile index")

class TabletView:
    def show_index_page(self): print("Tablet index")

class Dispatcher:
    def __init__(self):
        self.mobile = MobileView()
        self.tablet = TabletView()

    def dispatch(self, request):
        if request.type == "mobile": self.mobile.show_index_page()
        elif request.type == "tablet": self.tablet.show_index_page()
        else: print("Cannot dispatch")

class RequestController:
    def __init__(self): self.dispatcher = Dispatcher()
    def dispatch_request(self, request):
        if isinstance(request, Request):
            self.dispatcher.dispatch(request)
        else:
            print("Bad request")
```

`RequestController` is the single entry point. It validates, then delegates to a
dispatcher, which picks the appropriate view.

## Real-world examples

- **Django's URL resolver + middleware stack** is the textbook front controller for
  Python web apps.
- **Flask's `app.dispatch_request()`** routes to view functions through a
  middleware-aware front controller.
- **`click`** provides command groups that act as a front controller for CLI apps.

## Refactor recipe

When request handling is scattered across many entry points with duplicated
auth/logging/error-handling:

1. Define one entry function/class.
2. Move cross-cutting concerns (auth, logging, parsing) into it.
3. Replace direct entry calls with calls into the front controller.
4. Delegate the post-cross-cutting work to handler-per-type registry.

## Review checklist

- ✅ Cross-cutting concerns live in one place; handlers focus on business logic.
- ✅ Dispatch is data-driven (table) where possible, not `if/elif` chains.
- ❌ The front controller has accumulated business logic that belongs in handlers.
- ❌ Handlers also do auth/logging — the cross-cutting concerns are duplicated.
- ❌ The framework already provides this. Delete the custom layer.
