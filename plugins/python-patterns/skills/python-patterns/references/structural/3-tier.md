# 3-Tier Architecture

**TL;DR:** Strict separation between data, business logic, and presentation tiers.
Each tier only talks to its immediate neighbour.

**Category:** Structural (architectural)

## When to use

- Long-lived business application where presentation, rules, and storage evolve on
  different cadences.
- Multiple presentation layers (web, mobile, CLI) reuse the same business logic and
  storage.
- Strict separation discipline matters for compliance, audit, or team boundaries.

## When NOT to use (Pythonic alternatives first)

- **Small scripts.** Three tiers for a 200-line tool is ceremony.
- **Simple CRUD.** Many web frameworks (Django) bake their own variant of MVC; a hand-
  rolled 3-tier on top of Django duplicates work.
- **Prototype or research code.** Premature stratification slows iteration.
- **You actually want MVC.** MVC has *non-strict* relationships (controller talks to
  both); 3-tier is stricter. See `structural/mvc.md`.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/3-tier.py`), abridged:

```python
class Data:
    """Data tier."""
    products = {"milk": {"price": 1.50, "quantity": 10}, ...}

class BusinessLogic:
    """Business tier — the only thing that talks to Data."""
    data = Data()
    def product_list(self): return self.data["products"].keys()
    def product_information(self, product): return self.data["products"].get(product)

class Ui:
    """Presentation tier — only talks to BusinessLogic, never Data."""
    def __init__(self): self.business_logic = BusinessLogic()
    def get_product_list(self): ...
```

The contract: `Ui` must not import `Data`. Crossing the tier boundary is a bug.

## Real-world examples

- **Enterprise Java applications** ported to Python often retain a 3-tier shape
  because the business rules are codified in a tier separate from web/REST glue.
- **Django** loosely follows this with `models.py` (data + ORM), services / managers
  (business), and views/templates (presentation), though Django blends business into
  views by default.

## Refactor recipe

1. Identify code that crosses a boundary today (e.g., a view querying the DB
   directly).
2. Define the business interface that view should call instead.
3. Move the query into the business tier.
4. Update the view to call the business method.
5. Add a lint rule (`import-linter`, custom AST check) forbidding the bad import
   direction. Without enforcement the discipline erodes.

## Review checklist

- ✅ Presentation imports business; business imports data; data imports neither.
- ✅ Tier boundaries are documented and ideally enforced by tooling.
- ❌ The presentation tier reaches into the data tier "for performance". Performance
  optimization belongs behind the business interface, not bypassing it.
- ❌ The "business tier" is empty — calls just pass through. Either the abstraction is
  premature or the tier needs real logic.
- ❌ Cyclic imports between tiers. Break with an interface (Protocol) or move types.
