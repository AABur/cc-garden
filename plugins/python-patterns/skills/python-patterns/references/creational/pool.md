# Pool (Object Pool)

**TL;DR:** Pre-instantiate a set of expensive objects and recycle them, so creation
cost is amortized and resource usage is bounded.

**Category:** Creational

## When to use

- Object creation is **expensive** (network handshake, DB connection, OS-level resource
  allocation).
- The objects are **reusable** — calling `reset()` or simply re-using returns them to a
  clean state.
- Demand is **bursty but bounded** — many short-lived users, but you do not want to pay
  the creation cost each time *or* let usage grow unbounded.
- The cost of holding idle pooled objects is acceptable (memory vs. recreation
  trade-off).

## When NOT to use (Pythonic alternatives first)

- **`concurrent.futures.ThreadPoolExecutor` / `ProcessPoolExecutor`** already pool
  *workers*. For task execution, do not roll your own.
- **`multiprocessing.Pool`** for process pools.
- **Library-specific pools.** SQLAlchemy's `QueuePool`, `psycopg2`'s
  `ThreadedConnectionPool`, `httpx.Client`'s connection pooling — each ships a
  domain-tuned implementation. Use the library's pool, do not wrap a generic one.
- **You only need one instance.** That's a module-level value, not a pool.
- **You really need a queue.** `queue.Queue` is the data structure, not a pool — only
  use the *Pool pattern* when you also need acquire/release semantics with bounded
  capacity.

## Canonical implementation

From `faif/python-patterns` (`patterns/creational/pool.py`), abridged:

```python
from queue import Queue

class ObjectPool:
    def __init__(self, queue: Queue, auto_get: bool = False) -> None:
        self._queue = queue
        self.item = self._queue.get() if auto_get else None

    def __enter__(self) -> object:
        if self.item is None:
            self.item = self._queue.get()
        return self.item

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.item is not None:
            self._queue.put(self.item)
            self.item = None

# Usage
sample_queue: Queue[str] = Queue()
sample_queue.put("yam")
with ObjectPool(sample_queue) as obj:
    use(obj)            # 'yam' checked out
# obj is back in the pool here
```

The context manager handles acquire/release; `Queue` provides thread-safe handoff. The
example uses strings; in practice the queue holds connections, sessions, etc.

## Real-world examples

- **`sqlalchemy.pool.QueuePool`** — bounded connection pool with overflow and
  recycling.
- **`psycopg2.pool.ThreadedConnectionPool`** — Postgres connection pool.
- **`urllib3.PoolManager`** — connection pool for HTTP requests, also leveraged by
  `requests`.
- **`asyncio.Queue`-based worker pools** — task queue with N consumers, common in
  scrapers and pipelines.

## Refactor recipe

When you have repeated `Connection()` allocation in a hot loop:

1. **Look for an existing pool first** in your library of choice.
2. Wrap creation in a factory: `def new_conn(): return Connection(...)`.
3. Pre-fill a `Queue` with N pre-created connections.
4. Replace `conn = Connection()` / `conn.close()` with `with pool.acquire() as conn:`.
5. Add a graceful shutdown that drains the queue and calls `close()` on each.
6. Add metrics: queue size, wait time on acquire — these are the leading indicators
   that the pool is misconfigured.

## Review checklist

- ✅ Acquire/release are paired via context manager (no leaks if an exception is
  raised inside the block).
- ✅ Pool size is bounded by config; growth and idle behaviour are documented.
- ✅ Pooled objects expose a `reset()` (or are guaranteed stateless) before re-use.
- ✅ Shutdown closes pooled objects.
- ❌ The pool `Queue` blocks indefinitely on full — set a timeout and raise/log on
  exhaustion.
- ❌ The pool is rolled by hand when SQLAlchemy / urllib3 / library-X already provides
  one. Replace.
- ❌ Pooled objects retain mutable state from the previous user. Add a reset hook.
- ❌ The pool is module-level *and* tests do not reset it. Add a fixture.
