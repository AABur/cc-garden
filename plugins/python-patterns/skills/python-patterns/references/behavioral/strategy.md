# Strategy

**TL;DR:** Define a family of interchangeable algorithms; clients can swap them at
runtime. The algorithm varies independently from the client.

**Category:** Behavioral

## When to use

- The same task has multiple valid algorithms (sort orders, discount rules, retry
  policies, compression schemes).
- Choice of algorithm depends on runtime data (config, user choice, A/B test).
- New algorithms should be addable without changing client code.

## When NOT to use (Pythonic alternatives first)

- **Pass a function.** This is *the* most important Pythonic alternative. A "strategy"
  is a callable. `sorted(xs, key=lambda x: x.name)` is Strategy without ceremony.
- **`dict[str, Callable]`** for named-strategy lookup.
- **Library `functools.partial` or closures** for parameterized strategies.
- **Strategy *class* hierarchies** are appropriate when the algorithms carry persistent
  state, share helpers worth factoring, or need introspection a function lacks.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/strategy.py`), abridged. Note this
implementation is *Pythonic* — strategies are functions, not classes:

```python
from typing import Callable

class Order:
    def __init__(self, price: float, discount_strategy: Callable | None = None):
        self.price = price
        self.discount_strategy = discount_strategy

    def apply_discount(self) -> float:
        discount = self.discount_strategy(self) if self.discount_strategy else 0
        return self.price - discount

def ten_percent_discount(order: Order) -> float:
    return order.price * 0.10

def on_sale_discount(order: Order) -> float:
    return order.price * 0.25 + 20

# Usage
o = Order(100, discount_strategy=ten_percent_discount)
o.apply_discount()  # 90.0
```

Strategies are first-class functions. The upstream module also includes a
`DiscountStrategyValidator` descriptor that validates the strategy at assignment time
— a nice production pattern.

## Real-world examples

- **`sorted(..., key=fn)`** — `key` is a Strategy.
- **`logging.Formatter`** — formatters are Strategies for the format step.
- **Retry libraries** (`tenacity`, `urllib3.Retry`) — backoff strategies.
- **Compression in `requests`/`httpx`** — codec choice is a Strategy.
- **`functools.cmp_to_key`** turns old-style comparators into key-strategies.

## Refactor recipe

When a method is `if mode == "fast": ... elif mode == "slow": ...`:

1. Extract each branch into a function with a uniform signature.
2. Replace the conditional with a call to the chosen strategy.
3. (Optional) Build a `dict[str, Callable]` lookup for named strategies.
4. Decide if a class hierarchy is genuinely needed — usually it is not.
5. Document the protocol the strategy must satisfy (its expected signature).

## Review checklist

- ✅ Strategies share a clear contract (signature, return type).
- ✅ Strategies are pure where possible — easier to test, swap, parallelize.
- ✅ Validation that a chosen strategy is appropriate (descriptor, decorator, runtime
  check) is in place when stakes are high.
- ❌ A class hierarchy was used where functions sufficed. Simplify.
- ❌ Strategies share hidden global state, undermining the "swap freely" promise.
- ❌ The strategy's return shape varies across implementations; callers branch on
  type. Tighten the contract.
