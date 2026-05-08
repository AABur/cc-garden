# MVC (Model-View-Controller)

**TL;DR:** Separate data (Model), presentation (View), and the user-input glue
(Controller) so each varies independently.

**Category:** Structural (architectural)

## When to use

- Interactive applications with a UI: web, desktop, CLI.
- Multiple presentations of the same data (web + mobile + admin views).
- Test isolation matters — you want to test business logic without spinning up the
  UI.

## When NOT to use (Pythonic alternatives first)

- **Your framework already does it.** Django (loosely MVC, called MTV — model,
  template, view). Flask + templates. FastAPI + Pydantic models + routes. Use the
  framework's shape.
- **CLI script with no UI.** Hand-rolled MVC for a 100-line script is over-engineered.
- **You actually want strict 3-tier.** See `structural/3-tier.md` — MVC is *non-strict*
  (controller talks to both model and view).

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/mvc.py`), abridged:

```python
from abc import ABC, abstractmethod

class Model(ABC):
    @abstractmethod
    def __iter__(self): ...
    @abstractmethod
    def get(self, item: str) -> dict: ...

class View(ABC):
    @abstractmethod
    def show_item_list(self, item_type, items): ...
    @abstractmethod
    def show_item_information(self, item_type, name, info): ...
    @abstractmethod
    def item_not_found(self, item_type, name): ...

class Controller:
    def __init__(self, model: Model, view: View):
        self.model = model
        self.view = view

    def show_items(self):
        items = list(self.model)
        self.view.show_item_list(self.model.item_type, items)

    def show_item_information(self, name: str):
        try:
            info = self.model.get(name)
        except Exception:
            self.view.item_not_found(self.model.item_type, name)
        else:
            self.view.show_item_information(self.model.item_type, name, info)
```

The Controller orchestrates: it asks the Model for data and tells the View how to
present it. View and Model do not talk directly.

## Real-world examples

- **Django** uses MVC under the names model / template / view (the "view" is what
  most frameworks call a controller).
- **Flask** + Jinja templates form a hand-shaped MVC.
- **Tkinter** custom apps usually grow into MVC organically.
- **SwiftUI / React** with explicit "view-model" layers are MVVM, a close cousin.

## Refactor recipe

When a single class handles data, rendering, and input:

1. Pull the data access (DB, file, API) into a Model class.
2. Pull the rendering (HTML, console, GUI) into a View class with explicit methods.
3. Leave the Controller as the orchestrator that holds Model and View references and
   exposes user-action methods.
4. Tests can now drive the Controller with fake View/Model fixtures.

## Review checklist

- Good: Model knows nothing about View; View knows nothing about Model.
- Good: Controllers' methods correspond to user actions ("show item info", "save edit").
- Good: Views are easy to swap (web view, console view) without touching the Model or
  Controller.
- Bad: The View formats data the Model should produce. Logic leaked.
- Bad: The Controller has rendering code. Extract to View.
- Bad: The Model imports the View. Bad coupling; revisit boundaries.
