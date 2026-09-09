# std lib
# local
from dipworkpy.model import Order, OrderType

# under test
from dipworkpy.conflict_game import t_field_from_order, t_field, t_order

################################################
#
# t_field_from_order semantics:
#   - strength_a / strength_b are baseline ATTACK strengths; they are only
#     populated for active move orders (nmove / cmove). For everything else
#     (none / hld / hsup / msup / con) they stay at their pydantic default 0.
#   - defensive_strength and support_strength always carry the unit's base
#     strength, since hold/support/convoy can defend and contribute.
#   - original_order is always populated from the input Order.


def test_t_field_from_order_none():
    o = Order(nation="Au", utype="A", current="Vie")
    assert t_field_from_order(o) == t_field(
        player="Au",
        strength=1,
        name="Vie",
        order=t_order.none,
        dest="Vie",
        xref="Vie",
        strength_a=0,
        strength_b=0,
        defensive_strength=1,
        support_strength=1,
        original_order=o,
    )


def test_t_field_from_order_hold():
    o = Order(nation="Au", utype="A", current="Vie", order=OrderType.hld)
    assert t_field_from_order(o) == t_field(
        player="Au",
        strength=1,
        name="Vie",
        order=t_order.none,
        dest="Vie",
        xref="Vie",
        strength_a=0,
        strength_b=0,
        defensive_strength=1,
        support_strength=1,
        original_order=o,
    )
    o3 = Order(nation="Au", utype="3", current="Vie", order=OrderType.hld)
    assert t_field_from_order(o3) == t_field(
        player="Au",
        strength=3,
        name="Vie",
        order=t_order.none,
        dest="Vie",
        xref="Vie",
        strength_a=0,
        strength_b=0,
        defensive_strength=3,
        support_strength=3,
        original_order=o3,
    )


def test_t_field_from_order_nmove():
    o = Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Mun")
    assert t_field_from_order(o) == t_field(
        player="Au",
        strength=1,
        name="Vie",
        order=t_order.nmove,
        dest="Mun",
        xref="Mun",
        strength_a=1,
        strength_b=1,
        defensive_strength=1,
        support_strength=1,
        original_order=o,
    )
    o2 = Order(nation="Au", utype="2", current="Vie", order=OrderType.mve, dest="Mun")
    assert t_field_from_order(o2) == t_field(
        player="Au",
        strength=2,
        name="Vie",
        order=t_order.nmove,
        dest="Mun",
        xref="Mun",
        strength_a=2,
        strength_b=2,
        defensive_strength=2,
        support_strength=2,
        original_order=o2,
    )


def test_t_field_from_order_msup():
    o = Order(nation="Au", utype="A", current="Vie", order=OrderType.msup, dest="Mun")
    assert t_field_from_order(o) == t_field(
        player="Au",
        strength=1,
        name="Vie",
        order=t_order.msupport,
        dest="Mun",
        xref="Mun",
        strength_a=0,
        strength_b=0,
        defensive_strength=1,
        support_strength=1,
        original_order=o,
    )


def test_t_field_from_order_hsup():
    o = Order(nation="Au", utype="A", current="Vie", order=OrderType.hsup, dest="Mun")
    assert t_field_from_order(o) == t_field(
        player="Au",
        strength=1,
        name="Vie",
        order=t_order.hsupport,
        dest="Mun",
        xref="Mun",
        strength_a=0,
        strength_b=0,
        defensive_strength=1,
        support_strength=1,
        original_order=o,
    )


def test_t_field_from_order_con():
    o = Order(nation="Ge", utype="F", current="NTH", order=OrderType.con, dest="Kie")
    assert t_field_from_order(o) == t_field(
        player="Ge",
        strength=1,
        name="NTH",
        order=t_order.convoy,
        dest="Kie",
        xref="Kie",
        strength_a=0,
        strength_b=0,
        defensive_strength=1,
        support_strength=1,
        original_order=o,
    )


################################################


if __name__ == "__main__":
    import sys
    import pytest

    pytest.main(sys.argv)
