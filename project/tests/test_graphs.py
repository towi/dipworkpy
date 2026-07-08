# std python
import time
import random
from typing import Dict, Set

# under test
import dipworkpy.graphs as graphs


def test_find_path():
    """Test basic pathfinding functionality"""
    graph = {"A": {"B", "C"}, "B": {"C", "D"}, "C": {"D"}, "D": {"C"}, "E": {"F"}, "F": {"C"}}
    assert graphs.find_path(graph, "A", "D") is not None
    assert graphs.find_path(graph, "A", "E") is None
    assert graphs.find_path(graph, "A", "F") is None
    assert graphs.find_path(graph, "B", "A") is None


def test_find_shortest_path():
    """Test shortest path functionality"""
    graph = {"A": {"B", "C"}, "B": {"C", "D"}, "C": {"D"}, "D": {"C"}, "E": {"F"}, "F": {"C"}}
    assert graphs.find_shortest_path(graph, "A", "D") == ["A", "B", "D"]
    assert graphs.find_shortest_path(graph, "A", "E") is None
    assert graphs.find_shortest_path(graph, "A", "F") is None
    assert graphs.find_shortest_path(graph, "B", "A") is None


def test_find_path_empty_graph():
    """Test pathfinding with empty graph"""
    graph = {}
    assert graphs.find_path(graph, "A", "B") is None
    assert graphs.find_shortest_path(graph, "A", "B") is None


def test_find_path_self_loop():
    """Test pathfinding with self-loops"""
    graph = {"A": {"A", "B"}, "B": {"B", "C"}, "C": {"C"}}
    assert graphs.find_path(graph, "A", "A") == ["A"]
    assert graphs.find_shortest_path(graph, "B", "B") == ["B"]
    assert graphs.find_path(graph, "A", "C") == ["A", "B", "C"]


def test_find_path_multiple_routes():
    """Test pathfinding with multiple possible routes"""
    # Diamond pattern: A → B,C → D (two paths of same length)
    graph = {"A": {"B", "C"}, "B": {"D"}, "C": {"D"}, "D": set()}

    path1 = graphs.find_path(graph, "A", "D")
    path2 = graphs.find_shortest_path(graph, "A", "D")

    assert path1 is not None
    assert path2 is not None
    assert len(path1) == 3  # A → ? → D
    assert len(path2) == 3  # A → ? → D

    # Shortest path should prefer lexicographical order
    assert path2 == ["A", "B", "D"]  # B comes before C


def test_find_path_complex_diplomacy():
    """Test pathfinding with Diplomacy-like convoy scenario"""
    # Simulate: Army London → Brest via convoy through English Channel + Mid-Atlantic
    convoy_graph = {
        "Lon": {"ENG"},  # London connects to English Channel
        "ENG": {"Lon", "MAO"},  # English Channel connects to both
        "MAO": {"ENG", "Bre"},  # Mid-Atlantic connects to both
        "Bre": {"MAO"},  # Brest connects to Mid-Atlantic
    }

    path = graphs.find_shortest_path(convoy_graph, "Lon", "Bre")
    expected_path = ["Lon", "ENG", "MAO", "Bre"]

    assert path == expected_path
    assert len(path) == 4  # 3 convoy steps


def test_find_path_disconnected_components():
    """Test pathfinding with disconnected graph components"""
    graph = {
        "A": {"B"},
        "B": {"A"},  # Component 1
        "C": {"D"},
        "D": {"C"},  # Component 2
        "E": set(),  # Isolated node
    }

    # Within components should work
    assert graphs.find_path(graph, "A", "B") == ["A", "B"]
    assert graphs.find_path(graph, "C", "D") == ["C", "D"]

    # Between components should fail
    assert graphs.find_path(graph, "A", "C") is None
    assert graphs.find_path(graph, "A", "E") is None
    assert graphs.find_path(graph, "E", "A") is None


def test_make_graph_from_bi_edges():
    """Test bidirectional edge graph construction"""
    edges = {("A", "B"), ("B", "C"), ("C", "D")}
    allowed_nodes = {"A", "B", "C", "D"}

    graph = graphs.make_graph_from_bi_edges(edges, allowed_nodes)

    expected = {"A": {"B"}, "B": {"A", "C"}, "C": {"B", "D"}, "D": {"C"}}

    assert graph == expected


def test_make_graph_filtered_nodes():
    """Test graph construction with node filtering"""
    edges = {("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")}
    allowed_nodes = {"A", "B", "C"}  # Exclude D and E

    graph = graphs.make_graph_from_bi_edges(edges, allowed_nodes)

    # Should only include edges between allowed nodes
    expected = {"A": {"B"}, "B": {"A", "C"}, "C": {"B"}}

    assert graph == expected
    assert "D" not in graph
    assert "E" not in graph


def test_convoy_route_pathfinding():
    """Test convoy route pathfinding similar to Pascal ConvoyRoutePossible"""
    # Simulate complex convoy scenario with multiple possible routes
    convoy_map = {
        "Lon": {"ENG", "NTH"},  # London → English Channel, North Sea
        "ENG": {"Lon", "MAO", "Bre", "Pic"},  # English Channel hub
        "NTH": {"Lon", "HEL", "NWG", "Nwy"},  # North Sea hub
        "MAO": {"ENG", "Bre", "Spa", "Por"},  # Mid-Atlantic
        "HEL": {"NTH", "Kie", "Den"},  # Heligoland Bight
        "Bre": {"ENG", "MAO", "Pic"},  # Brest
        "Pic": {"ENG", "Bre"},  # Picardy
        "Spa": {"MAO", "Por"},  # Spain
        "Por": {"MAO", "Spa"},  # Portugal
        "Kie": {"HEL", "BAL"},  # Kiel
        "BAL": {"Kie", "Den", "Swe"},  # Baltic
        "Den": {"HEL", "BAL", "Swe"},  # Denmark
        "Swe": {"BAL", "Den", "NWG"},  # Sweden
        "NWG": {"NTH", "Swe", "Nwy"},  # Norwegian Sea
        "Nwy": {"NTH", "NWG"},  # Norway
    }

    # Test: Army London → Kiel (should find route via North Sea)
    path_to_kiel = graphs.find_shortest_path(convoy_map, "Lon", "Kie")
    assert path_to_kiel is not None
    assert path_to_kiel == ["Lon", "NTH", "HEL", "Kie"]

    # Test: Army London → Spain (should find route via English Channel)
    path_to_spain = graphs.find_shortest_path(convoy_map, "Lon", "Spa")
    assert path_to_spain is not None
    assert path_to_spain == ["Lon", "ENG", "MAO", "Spa"]

    # Test: Army London → Norway (multiple routes possible)
    path_to_norway = graphs.find_shortest_path(convoy_map, "Lon", "Nwy")
    assert path_to_norway is not None
    assert len(path_to_norway) == 3  # Lon → NTH → Nwy (direct route)


def _generate_large_graph(num_nodes: int, connectivity: float = 0.1) -> Dict[str, Set[str]]:
    """Generate a large random graph for performance testing"""
    # Create nodes
    nodes = [f"N{i:04d}" for i in range(num_nodes)]
    graph: Dict[str, Set[str]] = {node: set() for node in nodes}

    # Add random edges
    num_edges = int(num_nodes * (num_nodes - 1) * connectivity / 2)
    edges_added = 0

    while edges_added < num_edges:
        a = random.choice(nodes)
        b = random.choice(nodes)
        if a != b and b not in graph[a]:
            graph[a].add(b)
            graph[b].add(a)
            edges_added += 1

    return graph


def test_large_graph_performance():
    """Test pathfinding performance on large graphs"""
    print("\n=== Large Graph Performance Tests ===")

    test_sizes = [50, 200, 500]  # Smaller sizes for CI/automated testing

    for num_edges in test_sizes:
        print(f"\n--- Testing graph with ~{num_edges} edges ---")

        # Create test graph
        # For num_edges target, we need sqrt(num_edges) * 2 nodes approximately
        num_nodes = min(int((num_edges * 2) ** 0.5) + 1, 200)  # Cap nodes
        connectivity = num_edges / (num_nodes * (num_nodes - 1) / 2)
        connectivity = min(connectivity, 0.3)  # Reduce connectivity for faster generation

        print(f"Generating graph: {num_nodes} nodes, {connectivity:.3f} connectivity")

        start_time = time.time()
        graph = _generate_large_graph(num_nodes, connectivity)
        gen_time = time.time() - start_time

        # Count actual edges
        actual_edges = sum(len(neighbors) for neighbors in graph.values()) // 2
        print(f"Generated: {actual_edges} edges in {gen_time:.3f}s")

        # Test pathfinding performance
        start_node = f"N{0:04d}"
        end_node = f"N{num_nodes - 1:04d}"

        # Test find_path
        start_time = time.time()
        path1 = graphs.find_path(graph, start_node, end_node)
        find_time = time.time() - start_time

        # Test find_shortest_path
        start_time = time.time()
        path2 = graphs.find_shortest_path(graph, start_node, end_node)
        shortest_time = time.time() - start_time

        print(f"find_path: {find_time:.4f}s, path length: {len(path1) if path1 else 'None'}")
        print(f"find_shortest_path: {shortest_time:.4f}s, path length: {len(path2) if path2 else 'None'}")

        # Basic assertions
        if path1 and path2:
            assert len(path2) <= len(path1)  # Shortest should be <= any path

        # Performance assertion (should complete in reasonable time)
        assert find_time < 5.0, f"find_path took too long: {find_time:.3f}s"
        assert shortest_time < 10.0, f"find_shortest_path took too long: {shortest_time:.3f}s"


def test_edge_cases():
    """Test edge cases and error conditions"""

    # Empty graph
    empty_graph = {}
    assert graphs.find_path(empty_graph, "A", "B") is None
    assert graphs.find_shortest_path(empty_graph, "A", "B") is None

    # Single node
    single_node = {"A": set()}
    assert graphs.find_path(single_node, "A", "A") == ["A"]
    assert graphs.find_shortest_path(single_node, "A", "A") == ["A"]
    assert graphs.find_path(single_node, "A", "B") is None

    # Self-connected node
    self_loop = {"A": {"A"}}
    assert graphs.find_path(self_loop, "A", "A") == ["A"]
    assert graphs.find_shortest_path(self_loop, "A", "A") == ["A"]

    # Asymmetric graph (directed-like behavior)
    asymmetric = {"A": {"B"}, "B": {"C"}, "C": set()}
    assert graphs.find_path(asymmetric, "A", "C") == ["A", "B", "C"]
    assert graphs.find_path(asymmetric, "C", "A") is None

    # Very deep path
    linear_chain = {}
    for i in range(10):
        linear_chain[f"N{i}"] = {f"N{i + 1}"} if i < 9 else set()

    path = graphs.find_shortest_path(linear_chain, "N0", "N9")
    assert path is not None
    assert len(path) == 10
    assert path == [f"N{i}" for i in range(10)]


def test_diplomacy_convoy_scenarios():
    """Test realistic Diplomacy convoy scenarios"""

    # Classic England convoy: A London → Brest
    english_convoy = {"Lon": {"ENG"}, "ENG": {"Lon", "MAO", "Bre"}, "MAO": {"ENG", "Bre"}, "Bre": {"ENG", "MAO"}}

    path = graphs.find_shortest_path(english_convoy, "Lon", "Bre")
    assert path in [["Lon", "ENG", "Bre"], ["Lon", "ENG", "MAO", "Bre"]]
    assert len(path) <= 4

    # Complex multi-route convoy: A London → Constantinople
    complex_convoy = {
        "Lon": {"ENG", "NTH"},
        "ENG": {"Lon", "MAO", "WES"},
        "NTH": {"Lon", "BAL", "HEL"},
        "MAO": {"ENG", "WES", "LYO"},
        "WES": {"ENG", "MAO", "LYO", "TYS", "ION"},
        "LYO": {"MAO", "WES", "TYS"},
        "TYS": {"WES", "LYO", "ION"},
        "ION": {"WES", "TYS", "EAS", "AEG"},
        "EAS": {"ION", "AEG", "BLA"},
        "AEG": {"ION", "EAS", "BLA", "Con"},
        "BLA": {"EAS", "AEG", "Con"},
        "Con": {"AEG", "BLA"},
        "BAL": {"NTH", "HEL"},
        "HEL": {"NTH", "BAL"},
    }

    path = graphs.find_shortest_path(complex_convoy, "Lon", "Con")
    assert path is not None
    print(f"London → Constantinople convoy route: {' → '.join(path)} (length: {len(path)})")
    assert len(path) >= 6  # Should be reasonably long route


def test_performance_large_graphs(verbose: bool = False):
    """Test performance on large graphs (run with -v for timing output)"""
    if not verbose:
        return  # Skip performance tests unless verbose mode

    print("\n" + "=" * 60)
    print("LARGE GRAPH PERFORMANCE ANALYSIS")
    print("=" * 60)

    test_configs = [
        (100, "Small graph"),
        (1000, "Medium graph"),
        (10_000, "Large graph"),
        (100_000, "Huge graph"),
        (1_000_000, "Gigantic graph"),
    ]

    for num_edges, description in test_configs:
        print(f"\n{description} (~{num_edges} edges):")
        print("-" * 40)

        # Generate graph
        num_nodes = int((num_edges * 2) ** 0.5) + 1
        connectivity = min(num_edges / (num_nodes * (num_nodes - 1) / 2), 0.5)

        start_gen = time.time()
        graph = _generate_large_graph(num_nodes, connectivity)
        gen_time = time.time() - start_gen

        actual_edges = sum(len(neighbors) for neighbors in graph.values()) // 2

        print(f"Generation: {num_nodes} nodes, {actual_edges} edges in {gen_time:.3f}s")

        # Test pathfinding on specific node pairs for consistent timing
        start_node = f"N{0:04d}"
        end_node = f"N{min(num_nodes - 1, 50):04d}"  # Limit distance for reasonable time

        # Test find_path
        start_time = time.time()
        path1 = graphs.find_path(graph, start_node, end_node)
        find_time = time.time() - start_time

        # Test find_shortest_path
        start_time = time.time()
        path2 = graphs.find_shortest_path(graph, start_node, end_node)
        shortest_time = time.time() - start_time

        print(f"Pathfinding results ({start_node} → {end_node}):")
        print(f"  find_path: {find_time:.4f}s, length: {len(path1) if path1 else 'None'}")
        print(f"  find_shortest_path: {shortest_time:.4f}s, length: {len(path2) if path2 else 'None'}")

        if path1 and path2:
            print(f"  performance ratio: {shortest_time / find_time:.2f}x slower (shortest vs find)")

        # Performance assertion (should complete reasonably quickly)
        assert find_time < 2.0, f"find_path took too long: {find_time:.3f}s"
        assert shortest_time < 5.0, f"find_shortest_path took too long: {shortest_time:.3f}s"


if __name__ == "__main__":
    import sys
    import pytest

    # Check if verbose flag is present
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    if verbose:
        print("Running in verbose mode - including performance tests")
        test_performance_large_graphs(verbose=True)

    pytest.main(sys.argv)
