# Publish-Subscribe (Pub-Sub)

**TL;DR:** A broker decouples publishers from subscribers, routing messages by topic.
Publishers do not know who subscribes; subscribers do not know who publishes.

**Category:** Behavioral

## When to use

- Many independent producers and consumers should communicate without coupling.
- Topic-based routing fits the domain (events of a kind, channels, namespaces).
- Subscribers can be added/removed dynamically without coordinating with publishers.
- Asynchronous message flow is acceptable (the broker may queue).

## When NOT to use (Pythonic alternatives first)

- **Direct callbacks** if there is one publisher and a few stable subscribers — see
  `behavioral/observer.md`.
- **Dedicated brokers.** For real distributed work use Redis pub-sub, Kafka,
  RabbitMQ, NATS, AWS SNS/SQS, Google Pub/Sub. Do not roll your own.
- **`asyncio.Queue`** for in-process producer/consumer.
- **Framework signals.** Django Signals are pub-sub-shaped already.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/publish_subscribe.py`), abridged:

```python
class Provider:
    def __init__(self):
        self.msg_queue: list[str] = []
        self.subscribers: dict[str, list["Subscriber"]] = {}

    def notify(self, msg: str): self.msg_queue.append(msg)
    def subscribe(self, msg, subscriber):
        self.subscribers.setdefault(msg, []).append(subscriber)
    def unsubscribe(self, msg, subscriber):
        self.subscribers[msg].remove(subscriber)
    def update(self):
        for msg in self.msg_queue:
            for sub in self.subscribers.get(msg, []):
                sub.run(msg)
        self.msg_queue = []

class Publisher:
    def __init__(self, provider): self.provider = provider
    def publish(self, msg): self.provider.notify(msg)

class Subscriber:
    def __init__(self, name, provider):
        self.name, self.provider = name, provider
    def subscribe(self, msg): self.provider.subscribe(msg, self)
    def run(self, msg): print(f"{self.name} got {msg}")
```

`Provider` is the broker. `Publisher.publish("cartoon")` does not know who is
listening — `Provider.update()` later delivers messages to the topic's subscribers.

## Real-world examples

- **Redis pub-sub** for in-memory broadcasting between services.
- **Kafka** for durable, replayable event streams.
- **AWS SNS** + multiple SQS queues fan-out.
- **Postgres `LISTEN` / `NOTIFY`** for in-DB pub-sub.
- **Django Signals**, Flask Blinker — in-process pub-sub.

## Refactor recipe

When publishers and subscribers couple via direct references and the relationship is
many-to-many:

1. Introduce a broker (or use an existing one).
2. Convert direct calls to `broker.publish(topic, msg)`.
3. Subscribers register with `broker.subscribe(topic, handler)`.
4. Decide on delivery semantics: synchronous, queued, async — document the contract.
5. For inter-process / inter-service, prefer an established broker over rolling one.

## Review checklist

- Good: Topics are typed / enumerated; not free-form strings prone to typos.
- Good: Subscriber failures do not block other subscribers (the broker isolates them).
- Good: Delivery semantics are documented (at-most-once, at-least-once, ordered, …).
- Bad: The "broker" is a global mutable dict imported from everywhere — that is the
  Singleton anti-pattern in disguise.
- Bad: Subscribers leak — never unsubscribed, hold strong references.
- Bad: A real distributed broker is needed and the in-process toy is masquerading as
  one. Migrate.
