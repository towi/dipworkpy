"""
graphs helper module.

Examples see test_graphs.py.
"""

# std py
from typing import List, Dict, Set, Tuple, Iterable, Optional
from collections import deque


def find_path(graph: Dict[str, Set[str]], start: str, end: str, path: List[str] = []):
    """https://www.python.org/doc/essays/graphs/"""
    path = path + [start]
    if start == end:
        return path
    if start not in graph:
        return None
    for node in graph[start]:
        if node not in path:
            newpath = find_path(graph, node, end, path)
            if newpath:
                return newpath
    return None


def find_shortest_path_dfs(graph: Dict[str, Set[str]], start: str, end: str, path: List[str] = []):
    """if many short paths are possible, the lexicographical first one is selected
    recursive DFS based shortest path finder; easier to follow but sloooow on medium and large graphs.
    """
    path = path + [start]
    if start == end:
        return path
    if start not in graph:
        return None
    shortest = None
    for node in graph[start]:
        if node not in path:
            newpath = find_shortest_path_dfs(graph, node, end, path)
            if newpath:
                if not shortest:  # if not set yet
                    shortest = newpath
                elif len(newpath) == len(shortest):  # same len
                    if newpath < shortest:  # lex sorting
                        shortest = newpath
                elif len(newpath) < len(shortest):  # shorter
                    shortest = newpath
    return shortest


def make_graph_from_bi_edges(edges: Set[Tuple[str, str]], allowed_nodes: Set[str]) -> Dict[str, Set[str]]:
    """edges may refer to nodes that are not in allowed_nodes. those are filtered out."""
    graph: Dict[str, Set[str]] = {}
    for a, b in {(a, b) for a, b in edges if a in allowed_nodes and b in allowed_nodes}:
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    return graph


# KI:

def find_shortest_path_bfs(
        graph: Dict[str, Iterable[str]],
        start: str,
        end: str
) -> Optional[List[str]]:
    """Für ungewichtete Graphen findet BFS per Definition Pfade mit minimaler Kantenanzahl in O(V+E).
     Nachbarn sortiert verarbeiten, um bei gleichen Distanzen deterministisch den
     lexikografisch kleinsten Pfad zu bekommen.
    """
    if start == end:
        return [start]
    # Optional: Nachbarn einmalig vorsortieren statt bei jeder Iteration
    adj = {u: sorted(neigh) for u, neigh in graph.items()}
    q = deque([start])
    parent = {start: None}  # merkt den Vorgänger für Pfadrekonstruktion
    #
    while q:
        u = q.popleft()
        for v in adj.get(u, ()):
            if v not in parent:  # erstes Erreichen == kürzeste Distanz zu v
                parent[v] = u
                if v == end:  # frühzeitiges Beenden möglich
                    q.clear()
                    break
                q.append(v)
    if end not in parent:
        return None
    # Pfad rekonstruieren
    path = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return list(reversed(path))


# default algorithm:
find_shortest_path = find_shortest_path_bfs
