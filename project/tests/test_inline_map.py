from dipworkpy.geo_model import (
    Edge,
    FieldDef,
    FieldType,
    MapDefinition,
    Passable,
)
from dipworkpy.geography.map.inline import InlineMap


def _three_field_def() -> MapDefinition:
    return MapDefinition(
        fields={
            "A": FieldDef(name="A", type=FieldType.LA),
            "B": FieldDef(name="B", type=FieldType.LA),
            "C": FieldDef(name="C", type=FieldType.O),
        },
        edges={
            ("A", "B"): Edge(army=Passable.YES, fleet=Passable.NA, convoy_move=Passable.NO),
            ("B", "A"): Edge(army=Passable.YES, fleet=Passable.NA, convoy_move=Passable.NO),
            ("A", "C"): Edge(army=Passable.NO, fleet=Passable.YES, convoy_move=Passable.YES),
            ("C", "A"): Edge(army=Passable.NO, fleet=Passable.YES, convoy_move=Passable.YES),
        },
    )


def test_inline_map_field_exists():
    m = InlineMap(_three_field_def(), map_id="t1")
    assert m.field_exists("A")
    assert not m.field_exists("Z")


def test_inline_map_neighbors():
    m = InlineMap(_three_field_def())
    assert m.neighbors("A") == {"B", "C"}


def test_inline_map_army_passable():
    m = InlineMap(_three_field_def())
    assert m.army_passable("A", "B") is True
    assert m.army_passable("A", "C") is False


def test_inline_map_default_map_id():
    m = InlineMap(_three_field_def())
    assert m.map_id == "inline"
