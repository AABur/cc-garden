# Mediator

**TL;DR:** Centralize complex peer-to-peer communication between objects in a single
mediator object, so peers do not refer to each other directly.

**Category:** Behavioral

## When to use

- Many objects communicate in tangled M-to-N patterns; you want to flatten to N peers
  ↔ 1 mediator.
- Coordination logic ("if A says X, tell B and C, but only if D is in state Y") is
  growing across peers.
- You want to replace the coordinator at runtime (different chat protocols, different
  workflow engines).

## When NOT to use (Pythonic alternatives first)

- **A list of callbacks** is enough for simple "broadcast" cases. See
  `behavioral/observer.md`.
- **An event bus / pub-sub** if peers do not need to know each other and the
  coordination is "fire and forget". See `behavioral/publish_subscribe.md`.
- **The mediator becomes a god object.** A single class that knows everyone's protocol
  smells like the anti-pattern from `references/anti-patterns.md`.

## Canonical implementation

From `faif/python-patterns` (`patterns/behavioral/mediator.py`), abridged:

```python
from __future__ import annotations

class ChatRoom:
    """Mediator class"""
    def display_message(self, user: User, message: str) -> str:
        return f"[{user} says]: {message}"

class User:
    def __init__(self, name: str) -> None:
        self.name = name
        self.chat_room = ChatRoom()

    def say(self, message: str) -> str:
        return self.chat_room.display_message(self, message)

    def __str__(self) -> str: return self.name
```

`User` instances do not talk to each other directly — they go through `ChatRoom`. The
mediator knows the rules of interaction.

## Real-world examples

- **Tkinter event handlers** route through the root window / Tk mainloop, the
  mediator for UI events.
- **GUI form coordinators** that update related fields when one field changes.
- **Workflow engines** (Airflow, Prefect) where the mediator is the scheduler that
  orchestrates tasks.
- **WebSocket chat servers** where the room object mediates participants.

## Refactor recipe

When peers reference each other in tangled webs:

1. List all peer-to-peer interactions and identify the patterns ("when A does X, B
   reacts").
2. Extract those reactions into a Mediator class.
3. Each peer holds a reference to the mediator, not to other peers.
4. Each peer calls `self.mediator.something(self, ...)`; the mediator does the
   coordination.
5. If the mediator grows to handle many unrelated workflows, split it.

## Review checklist

- Good: Peers do not import or reference each other.
- Good: The mediator's responsibility is *coordination*, not the peers' business logic.
- Good: The mediator has clear, named methods per workflow ("post_message",
  "kick_user").
- Bad: The mediator has accumulated business logic that belongs in peers.
- Bad: The mediator is one giant `if sender_type == ...: elif ...:` cascade. Split or
  refactor.
- Bad: Used where pub-sub or simple callbacks would suffice; ceremony in disguise.
