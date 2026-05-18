from dipworkpy.geo_model import FieldType, MapDefinition, MapRef
from dipworkpy.geography.convoy import build_convoy_graph
from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.geography.map.inline import InlineMap
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.rules import can_reach_by_unit
from dipworkpy.model import Order, OrderType


def test_field_local_schema_does_not_require_redundant_field_name() -> None:
    mdef = MapDefinition.model_validate(
        {
            "fields": {
                "Vie": {"type": "LA", "borders": {"Boh": ["A"]}},
                "Boh": {"type": "L", "borders": {"Vie": ["A"]}},
            }
        }
    )
    inline = InlineMap(mdef)

    assert inline.field_exists("Vie")
    assert mdef.fields["Vie"].name == "Vie"


def test_convoy_candidates_normalize_subfield_order_endpoints_to_superfields() -> None:
    m = resolve_map_ref(MapRef())
    orders = [
        Order(nation="Fr", utype="A", current="SpN", order=OrderType.mve, dest="Tun"),
        Order(nation="Fr", utype="F", current="MID", order=OrderType.con, dest="SpN"),
        Order(nation="Fr", utype="F", current="WMS", order=OrderType.con, dest="SpN"),
    ]

    graph = build_convoy_graph(orders, m)

    assert ("Spa", "MID") in graph.coastal_edges
    assert 0 in graph.cmove_candidates


def test_armies_cannot_be_hosted_on_split_coast_subfields() -> None:
    m = resolve_map_ref(MapRef())
    assert m.field_type("BuE") == FieldType.LC
    assert can_reach_by_unit("BuE", "Con", "A", m) is False
    assert can_reach_by_unit("BuS", "Gre", "A", m) is False
    assert can_reach_by_unit("PeS", "Fin", "A", m) is False


def test_geography_phase_normalizes_convoy_companion_lookup_to_superfields() -> None:
    resp = geography_phase(
        GeographyRequest(
            orders=[
                Order(nation="Fr", utype="A", current="SpN", order=OrderType.mve, dest="Tun"),
                Order(nation="Fr", utype="F", current="MID", order=OrderType.con, dest="SpN"),
                Order(nation="Fr", utype="F", current="WMS", order=OrderType.con, dest="SpN"),
            ]
        )
    )

    assert resp.order_geo_info[0].is_convoy_move is True
    assert resp.order_geo_info[1].is_valid is True
    assert resp.order_geo_info[2].is_valid is True


def test_tyrrhenian_sea_is_sea_for_fleet_and_convoy() -> None:
    m = resolve_map_ref(MapRef())
    assert m.field_type("TYS") == FieldType.O
    assert can_reach_by_unit("TYS", "ION", "F", m) is True
    assert can_reach_by_unit("TYS", "ION", "A", m) is False
