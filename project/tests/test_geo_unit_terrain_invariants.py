from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.rules import can_reach_by_unit


def test_armies_cannot_use_sea_or_subfield_destinations_even_if_source_data_has_border() -> None:
    m = resolve_map_ref(MapRef())
    assert can_reach_by_unit("NAT", "MID", "A", m) is False
    assert can_reach_by_unit("Gas", "SpN", "A", m) is False
    assert can_reach_by_unit("Con", "BuE", "A", m) is False


def test_fleets_cannot_enter_inland_land_even_if_neighbor_exists() -> None:
    m = resolve_map_ref(MapRef())
    assert can_reach_by_unit("Vie", "Boh", "F", m) is False
    assert can_reach_by_unit("Mun", "Boh", "F", m) is False
