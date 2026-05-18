from dipworkpy.geo_model import MapRef
from dipworkpy.geography.coast import resolve_coast
from dipworkpy.geography.map.resolve import resolve_map_ref
from dipworkpy.geography.model import RetreatOptionsRequest
from dipworkpy.geography.retreat import retreat_options
from dipworkpy.geography.rules import can_reach_by_unit
from dipworkpy.model import Order, OrderType


def _move(current: str, dest: str, utype: str) -> Order:
    return Order(nation="Fr", utype=utype, current=current, order=OrderType.mve, dest=dest)


def test_spain_from_gas_army_uses_superfield_fleet_diverts_to_north_coast() -> None:
    m = resolve_map_ref(MapRef())
    assert can_reach_by_unit("Gas", "Spa", "A", m) is True
    assert can_reach_by_unit("Gas", "SpN", "A", m) is False
    assert can_reach_by_unit("Gas", "Spa", "F", m) is True
    assert resolve_coast(_move("Gas", "Spa", "F"), m) == "SpN"


def test_spain_from_mar_army_uses_superfield_fleet_diverts_to_south_coast() -> None:
    m = resolve_map_ref(MapRef())
    assert can_reach_by_unit("Mar", "Spa", "A", m) is True
    assert can_reach_by_unit("Mar", "SpS", "A", m) is False
    assert can_reach_by_unit("Mar", "Spa", "F", m) is True
    assert resolve_coast(_move("Mar", "Spa", "F"), m) == "SpS"


def test_spain_from_por_and_mid_fleet_to_superfield_is_ambiguous() -> None:
    m = resolve_map_ref(MapRef())
    assert can_reach_by_unit("Por", "Spa", "A", m) is True
    assert can_reach_by_unit("Por", "Spa", "F", m) is True
    assert resolve_coast(_move("Por", "Spa", "F"), m) is None
    assert can_reach_by_unit("MID", "Spa", "A", m) is False
    assert can_reach_by_unit("MID", "Spa", "F", m) is True
    assert resolve_coast(_move("MID", "Spa", "F"), m) is None


def test_bulgaria_from_con_has_army_superfield_and_fleet_split_coasts() -> None:
    m = resolve_map_ref(MapRef())
    assert can_reach_by_unit("Con", "Bul", "A", m) is True
    assert can_reach_by_unit("Con", "BuE", "A", m) is False
    assert can_reach_by_unit("Con", "BuS", "A", m) is False
    assert can_reach_by_unit("Con", "Bul", "F", m) is True
    assert can_reach_by_unit("Con", "BuE", "F", m) is True
    assert can_reach_by_unit("Con", "BuS", "F", m) is True
    assert resolve_coast(_move("Con", "Bul", "F"), m) is None


def test_fin_pet_army_superfield_and_fleet_south_coast() -> None:
    m = resolve_map_ref(MapRef())
    assert can_reach_by_unit("Fin", "Pet", "A", m) is True
    assert can_reach_by_unit("Fin", "PeS", "A", m) is False
    assert can_reach_by_unit("Fin", "Pet", "F", m) is True
    assert resolve_coast(_move("Fin", "Pet", "F"), m) == "PeS"


def test_mar_retreat_candidates_filter_super_or_subfield_by_unit_type() -> None:
    army = retreat_options(RetreatOptionsRequest(field="Mar", attacked_from="Gas", utype="A"))
    fleet = retreat_options(RetreatOptionsRequest(field="Mar", attacked_from="Gas", utype="F"))

    assert "Spa" in army.candidates
    assert "SpS" not in army.candidates
    assert "SpS" in fleet.candidates
    assert "Spa" not in fleet.candidates
