from dipworkpy.geo_model import MapRef
from dipworkpy.geography.convoy import (
    build_convoy_graph,
    classify_cmove_candidates,
    convoy_route_exists,
)
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.model import Order, OrderType


def test_empty_graph_with_no_convoy_orders():
    m = resolve_map_ref(MapRef())
    orders = [Order(nation="Au", utype="A", current="Vie", order=OrderType.hld)]
    g = build_convoy_graph(orders, m)
    assert g.convoyer_fields == set()


def test_graph_includes_convoyer():
    m = resolve_map_ref(MapRef())
    orders = [
        Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="Bel"),
        Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Lon"),
    ]
    g = build_convoy_graph(orders, m)
    assert "NTH" in g.convoyer_fields
    assert 0 in g.cmove_candidates  # Lon->Bel classified as cmove


def test_classify_cmove_no_convoy_no_candidate():
    m = resolve_map_ref(MapRef())
    orders = [Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Tyr")]
    cmoves = classify_cmove_candidates(orders, m)
    assert cmoves == set()


def test_cmove_requires_actual_convoy_graph_route():
    m = resolve_map_ref(MapRef())
    orders = [
        Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="Bel"),
        Order(nation="It", utype="F", current="ION", order=OrderType.con, dest="Lon"),
    ]
    assert classify_cmove_candidates(orders, m) == set()


def test_convoy_graph_supports_multi_sea_route():
    m = resolve_map_ref(MapRef())
    orders = [
        Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="Bre"),
        Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Lon"),
        Order(nation="En", utype="F", current="ENG", order=OrderType.con, dest="Lon"),
    ]
    graph = build_convoy_graph(orders, m)
    assert ("ENG", "NTH") in graph.sea_edges
    assert ("Lon", "NTH") in graph.coastal_edges
    assert ("ENG", "Bre") in graph.coastal_edges
    assert 0 in graph.cmove_candidates
    assert convoy_route_exists("Lon", "Bre", graph) is True
