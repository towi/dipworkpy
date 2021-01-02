# std lib
# local
from dipworkpy.model import Order, OrderType
# under test
from dipworkpy.conflict_game import t_field_from_order, t_field, t_order

################################################


def test_t_field_from_order_none():
    assert ( t_field_from_order(Order(nation="Au", utype="A", current="Vie"))
            == t_field(player="Au", strength=1, name="Vie", order=t_order.none, dest="Vie", xref="Vie", strength_a=1, strength_b=1, defensive_strength=1, support_strength=1) )


def test_t_field_from_order_hold():
    assert ( t_field_from_order(Order(nation="Au", utype="A", current="Vie", order=OrderType.hld))
            == t_field(player="Au", strength=1, name="Vie", order=t_order.none, dest="Vie", xref="Vie", strength_a=1, strength_b=1, defensive_strength=1, support_strength=1) )
    assert ( t_field_from_order(Order(nation="Au", utype="3", current="Vie", order=OrderType.hld))
            == t_field(player="Au", strength=3, name="Vie", order=t_order.none, dest="Vie", xref="Vie", strength_a=3, strength_b=3, defensive_strength=3, support_strength=3) )


def test_t_field_from_order_nmove():
    assert ( t_field_from_order(Order(nation="Au", utype="A", current="Vie", order=OrderType.mve, dest="Mun"))
             == t_field(player="Au", strength=1, name="Vie", order=t_order.nmove, dest="Mun", xref="Mun", strength_a=0, strength_b=0, defensive_strength=1, support_strength=1) )
    assert ( t_field_from_order(Order(nation="Au", utype="2", current="Vie", order=OrderType.mve, dest="Mun"))
             == t_field(player="Au", strength=2, name="Vie", order=t_order.nmove, dest="Mun", xref="Mun", strength_a=0, strength_b=0, defensive_strength=2, support_strength=2) )


def test_t_field_from_order_msup():
    assert ( t_field_from_order(Order(nation="Au", utype="A", current="Vie", order=OrderType.msup, dest="Mun"))
             == t_field(player="Au", strength=1, name="Vie", order=t_order.msupport, dest="Mun", xref="Mun", strength_a=1, strength_b=1, defensive_strength=1, support_strength=1) )


def test_t_field_from_order_hsup():
    assert ( t_field_from_order(Order(nation="Au", utype="A", current="Vie", order=OrderType.hsup, dest="Mun"))
             == t_field(player="Au", strength=1, name="Vie", order=t_order.hsupport, dest="Mun", xref="Mun", strength_a=1, strength_b=1, defensive_strength=1, support_strength=1) )


def test_t_field_from_order_con():
    assert ( t_field_from_order(Order(nation="Ge", utype="F", current="NTH", order=OrderType.con, dest="Kie"))
             == t_field(player="Ge", strength=1, name="NTH", order=t_order.convoy, dest="Kie", xref="Kie", strength_a=1, strength_b=1, defensive_strength=1, support_strength=1) )

################################################


if __name__ == "__main__":
    import sys
    import pytest
    pytest.main(sys.argv)
