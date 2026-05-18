from dipworkpy.geo_model import Edge, FieldDef, FieldType, MapDefinition, MapRef, Passable
from dipworkpy.geography.convoy import build_convoy_graph, convoy_route_exists
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.model import Order, OrderType


def _convoy_map() -> MapRef:
    fields = {
        "Spa": FieldDef(name="Spa", type=FieldType.LC, subfields=["SpN", "SpS"], features=["$convoyable"]),
        "SpN": FieldDef(name="SpN", type=FieldType.LCF, sub_of="Spa"),
        "SpS": FieldDef(name="SpS", type=FieldType.LCF, sub_of="Spa"),
        "Tun": FieldDef(name="Tun", type=FieldType.LC, features=["$convoyable"]),
        "MID": FieldDef(name="MID", type=FieldType.O, features=["$convoying"]),
        "WMS": FieldDef(name="WMS", type=FieldType.O, features=["$convoying"]),
    }
    edges = {
        ("Spa", "MID"): Edge(army=Passable.NO, fleet=Passable.NO, convoy_move=Passable.YES),
        ("SpN", "MID"): Edge(army=Passable.NA, fleet=Passable.YES, convoy_move=Passable.YES),
        ("SpS", "WMS"): Edge(army=Passable.NA, fleet=Passable.YES, convoy_move=Passable.YES),
        ("MID", "WMS"): Edge(army=Passable.NA, fleet=Passable.YES, convoy_move=Passable.YES),
        ("WMS", "Tun"): Edge(army=Passable.YES, fleet=Passable.YES, convoy_move=Passable.YES),
    }
    return MapRef(inline_map=MapDefinition(fields=fields, edges=edges))


def test_convoy_graph_normalizes_coastal_subfields_to_superfields() -> None:
    m = resolve_map_ref(_convoy_map())
    orders = [
        Order(nation="Fr", utype="A", current="Spa", order=OrderType.mve, dest="Tun"),
        Order(nation="Fr", utype="F", current="MID", order=OrderType.con, dest="Spa"),
        Order(nation="Fr", utype="F", current="WMS", order=OrderType.con, dest="Spa"),
    ]

    graph = build_convoy_graph(orders, m)

    assert ("Spa", "MID") in graph.coastal_edges
    assert ("SpN", "MID") not in graph.coastal_edges
    assert ("SpS", "WMS") not in graph.coastal_edges
    assert convoy_route_exists("Spa", "Tun", graph) is True
    assert graph.cmove_candidates == {0}


def test_convoy_graph_uses_explicit_convoy_marker_not_fleet_passability() -> None:
    m = resolve_map_ref(_convoy_map())
    assert m.convoy_passable("Spa", "MID") is True
    assert m.fleet_passable("Spa", "MID") == Passable.NO
