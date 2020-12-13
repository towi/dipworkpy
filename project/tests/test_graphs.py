# under test
# local
#  under test
import dipworkpy.graphs as graphs


def test_find_path():
    graph = {
        'A': {'B', 'C'},
        'B': {'C', 'D'},
        'C': {'D'},
        'D': {'C'},
        'E': {'F'},
        'F': {'C'}
    }
    assert graphs.find_path(graph, 'A', 'D') is not None
    assert graphs.find_path(graph, 'A', 'E') is None
    assert graphs.find_path(graph, 'A', 'F') is None
    assert graphs.find_path(graph, 'B', 'A') is None


def test_find_shortest_path():
    graph = {
        'A': {'B', 'C'},
        'B': {'C', 'D'},
        'C': {'D'},
        'D': {'C'},
        'E': {'F'},
        'F': {'C'}
    }
    assert graphs.find_shortest_path(graph, 'A', 'D') == ['A', 'B', 'D']
    assert graphs.find_shortest_path(graph, 'A', 'E') is None
    assert graphs.find_shortest_path(graph, 'A', 'F') is None
    assert graphs.find_shortest_path(graph, 'B', 'A') is None


if __name__ == "__main__":
    import sys
    import pytest
    pytest.main(sys.argv)
