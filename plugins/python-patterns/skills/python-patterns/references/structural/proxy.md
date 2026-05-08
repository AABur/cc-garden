# Proxy

**TL;DR:** Stand in for another object to control access, add cross-cutting
concerns (logging, caching, auth), or defer expensive work.

**Category:** Structural

## When to use

- **Access control / auth.** Protection proxy gating a sensitive resource.
- **Logging / metrics.** Observability proxy that records calls.
- **Caching.** Memoization proxy for expensive results.
- **Lazy loading.** Virtual proxy that defers construction of the real subject until
  needed.
- **Remote.** Stub proxy that forwards to a remote service (RPC).

## When NOT to use (Pythonic alternatives first)

- **Decorator vs Proxy.** Decorator *adds* behaviour; Proxy *gates* or *substitutes*.
  When the wrapped object's interface and lifecycle are largely unchanged but you
  insert checks, it is a Proxy. See `structural/decorator.md` for the contrast.
- **A property is enough.** For a single attribute that needs lazy evaluation, see
  `creational/lazy_evaluation.md` — `@cached_property`.
- **Library already proxies.** `unittest.mock.MagicMock`, `httpx`, `requests` —
  many domains have idiomatic proxies; do not reinvent.
- **You actually want Adapter.** If the interface changes, see `structural/adapter.md`.

## Canonical implementation

From `faif/python-patterns` (`patterns/structural/proxy.py`), abridged:

```python
class Subject:
    def do_the_job(self, user: str) -> None:
        raise NotImplementedError

class RealSubject(Subject):
    def do_the_job(self, user: str) -> None:
        print(f"Job for {user}")

class Proxy(Subject):
    def __init__(self) -> None:
        self._real_subject = RealSubject()

    def do_the_job(self, user: str) -> None:
        print(f"[log] requested by {user}")
        if user == "admin":
            self._real_subject.do_the_job(user)
        else:
            print("[log] denied")
```

The proxy implements the same `Subject` interface; clients use `Proxy` or
`RealSubject` interchangeably. Auth and logging are added by the proxy without
changing the real subject.

## Real-world examples

- **`unittest.mock.Mock`** — test doubles that proxy method calls.
- **`weakref.proxy(obj)`** — stdlib weak-reference proxy.
- **SQLAlchemy lazy-loading relationships** — the related object is a proxy until
  accessed.
- **`functools.lru_cache`** as a caching proxy over a function.
- **gRPC / xmlrpc.client stubs** as remote proxies.

## Refactor recipe

To add logging / auth / caching to an existing class without touching it:

1. Define a Proxy class with the same interface (Protocol or shared ABC).
2. Hold the real subject internally.
3. In each method, perform the cross-cutting concern, then delegate.
4. Replace direct uses with the proxy at the boundary; the rest of the code is
   unchanged.

## Review checklist

- ✅ Proxy and real subject share an interface (formal Protocol or duck-typed).
- ✅ Cross-cutting concerns are isolated in the proxy; the real subject stays clean.
- ✅ Tests cover both "proxy in" and "real subject only" paths.
- ❌ The proxy mutates the real subject's state in surprising ways.
- ❌ The proxy bypasses the real subject in some methods, leading to inconsistent
  behaviour.
- ❌ Multiple proxies chain unintentionally; debugging becomes archaeology. Add a
  `__repr__` revealing the chain.
