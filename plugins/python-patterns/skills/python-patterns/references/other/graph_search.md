# Graph Search

**TL;DR:** Algorithmic templates for traversing graphs — depth-first search (DFS),
breadth-first search (BFS), shortest-path. Not a GoF pattern; a small library of
graph algorithms.

**Category:** Other (algorithm, non-GoF)

## When to use

- You need to find paths, reachability, or cycles in a graph.
- BFS for shortest path in unweighted graphs.
- DFS for path existence, all paths, topological sort.

## When NOT to use (Pythonic alternatives first)

- **`networkx`** is the standard library for graph work in Python. Use it unless you
  have a strong reason not to.
- **`graph-tool`, `igraph`** for performance-critical graph processing.
- **Custom algorithms** only when you have a reason: tight memory budget, embedded
  constraints, or pedagogy.

## Canonical implementation

From `faif/python-patterns` (`patterns/other/graph_search.py`), abridged:

```python
from typing import Optional

class GraphSearch:
    def __init__(self, graph: dict[str, list[str]]) -> None:
        self.graph = graph

    def find_path_dfs(self, start, end, path=None) -> Optional[list[str]]:
        path = path or []
        path.append(start)
        if start == end: return path
        for node in self.graph.get(start, []):
            if node not in path:
                newpath = self.find_path_dfs(node, end, path[:])
                if newpath: return newpath

    def find_shortest_path_bfs(self, start, end) -> Optional[list[str]]:
        queue = [start]; dist_to = {start: 0}; edge_to = {}
        if start == end: return queue
        while queue:
            value = queue.pop(0)
            for node in self.graph[value]:
                if node not in dist_to:
                    edge_to[node] = value
                    dist_to[node] = dist_to[value] + 1
                    queue.append(node)
                    if end in edge_to:
                        path = []; node = end
                        while dist_to[node] != 0:
                            path.insert(0, node); node = edge_to[node]
                        path.insert(0, start)
                        return path
```

DFS recurses through neighbours; BFS uses a queue and edge-to map to reconstruct the
shortest path.

## Real-world examples

- **`networkx.shortest_path`** — the production answer for almost all use cases.
- **Build systems** (Make, Bazel) traverse dependency graphs.
- **Package managers** (pip, npm) resolve dependency graphs.
- **Routing / pathfinding** in games and maps (often A*, an extension of BFS with a
  heuristic).

## Refactor recipe

When you have hand-rolled graph traversal scattered across the codebase:

1. Model the graph explicitly — `dict[node, list[node]]` adjacency, or the equivalent
   in `networkx`.
2. Replace ad-hoc traversal with a library call (`networkx.shortest_path` and
   friends).
3. Keep custom traversal only where requirements force it (streaming, distributed,
   exotic constraints).

## Review checklist

- Good: Graph representation is consistent and documented.
- Good: Cycles are handled — DFS without a visited set will recurse forever.
- Good: For shortest path on weighted graphs, an appropriate algorithm is used (Dijkstra,
  Bellman-Ford). Plain BFS is wrong.
- Bad: Recursion depth grows with the graph and hits Python's recursion limit. Convert
  to an explicit stack.
- Bad: Custom DFS is slower / less correct than `networkx`. Consider migrating.
- Bad: "Graph" is actually a tree; tree-specific algorithms are simpler and more efficient.
