from dipworkpy.geo_model import (
    FieldDef,
    FieldType,
    MapDefinition,
    MapRef,
)
from dipworkpy.geography.map.resolve import resolve_map_ref


def test_resolve_default_returns_standard():
    m = resolve_map_ref(MapRef())
    assert m.map_id == "standard"


def test_resolve_by_id():
    m = resolve_map_ref(MapRef(map_id="standard"))
    assert m.map_id == "standard"


def test_inline_wins_over_id():
    inline = MapDefinition(fields={"X": FieldDef(name="X", type=FieldType.L)}, edges={})
    m = resolve_map_ref(MapRef(map_id="standard", inline_map=inline))
    assert m.map_id == "inline"
    assert m.field_exists("X")
    assert not m.field_exists("Vie")
