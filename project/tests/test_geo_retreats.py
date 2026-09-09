from dipworkpy.geo_model import Edge, FieldDef, FieldType, MapDefinition, MapRef, Passable
from dipworkpy.geography.model import RetreatOptionsRequest
from dipworkpy.geography.retreat import retreat_options


def _boh_ring_map() -> MapRef:
    ring = ["Sil", "Gal", "Vie", "Tri", "Mun"]
    fields = {
        "Boh": FieldDef(name="Boh", type=FieldType.L, neighbor_order=ring),
        **{name: FieldDef(name=name, type=FieldType.L) for name in ring},
    }
    edges = {("Boh", name): Edge(army=Passable.YES, fleet=Passable.NA, convoy_move=Passable.NA) for name in ring}
    return MapRef(inline_map=MapDefinition(fields=fields, edges=edges))


def test_retreat_options_follow_right_hand_rule_from_attack_direction() -> None:
    resp = retreat_options(RetreatOptionsRequest(field="Boh", attacked_from="Sil", map=_boh_ring_map()))

    assert resp.candidates == ["Gal", "Mun", "Vie", "Tri", "ex"]


def test_retreat_options_filter_occupied_and_pattfields_but_keep_ex() -> None:
    resp = retreat_options(
        RetreatOptionsRequest(
            field="Boh",
            attacked_from="Sil",
            occupied_fields={"Gal", "Mun", "Vie", "Tri"},
            map=_boh_ring_map(),
        )
    )

    assert resp.candidates == ["ex"]


def test_retreat_options_use_unit_passability() -> None:
    resp = retreat_options(
        RetreatOptionsRequest(
            field="Boh",
            attacked_from="Sil",
            utype="F",
            map=_boh_ring_map(),
        )
    )

    assert resp.candidates == ["ex"]
