"""
graphs helper module.

Examples see test_graphs.py.
"""

# std py
from typing import List, Dict, Set, Tuple


def find_path(graph : Dict[str,Set[str]], start:str, end:str, path:List[str]=[]):
    """https://www.python.org/doc/essays/graphs/"""
    path = path + [start]
    if start == end:
        return path
    if not start in graph:
        return None
    for node in graph[start]:
        if node not in path:
            newpath = find_path(graph, node, end, path)
            if newpath: return newpath
    return None


def find_shortest_path(graph:Dict[str,Set[str]], start:str, end:str, path:List[str]=[]):
    """if many short paths are possible, the lexicographical first one is selected."""
    path = path + [start]
    if start == end:
        return path
    if not start in graph:
        return None
    shortest = None
    for node in graph[start]:
        if node not in path:
            newpath = find_shortest_path(graph, node, end, path)
            if newpath:
                if not shortest: # if not set yet
                    shortest = newpath
                elif len(newpath) == len(shortest):  # same len
                    if newpath < shortest: # lex sorting
                        shortest = newpath
                elif len(newpath) < len(shortest): # shorter
                    shortest = newpath
    return shortest


def make_graph_from_bi_edges(edges: Set[Tuple[str,str]], allowed_nodes:Set[str]) -> Dict[str,Set[str]]:
    """edges may refer to nodes that are not in allowed_nodes. those are filtered out."""
    graph: Dict[str, Set[str]] = {}
    for a, b in {(a, b) for a, b in edges if a in allowed_nodes and b in allowed_nodes}:
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    return graph
