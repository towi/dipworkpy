from dipworkpy.conflict_game import conflict_game
from dipworkpy.geo_model import ConvoyGraph, OrderGeoInfo
from dipworkpy.model import Order, OrderType, Situation


def _valid(i: int) -> OrderGeoInfo:
    return OrderGeoInfo(order_index=i, is_valid=True, effective_behavior="moves")


def test_conflict_uses_convoy_graph_after_convoyer_dislodgement() -> None:
    orders = [
        Order(nation="En", utype="A", current="Edi", order=OrderType.mve, dest="Bel"),
        Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Edi"),
        # Extra ordered convoyer for the same army, but geographically disconnected.
        # The old 'always' routing accepted the army move if any convoyer survived.
        Order(nation="En", utype="F", current="ION", order=OrderType.con, dest="Edi"),
        Order(nation="Ge", utype="F", current="ENG", order=OrderType.mve, dest="NTH"),
        Order(nation="Ge", utype="F", current="Lon", order=OrderType.msup, dest="ENG"),
    ]
    graph = ConvoyGraph(
        coastal_edges={("Edi", "NTH"), ("NTH", "Bel")},
        convoyer_fields={"NTH", "ION"},
        cmove_candidates={0},
    )

    result = conflict_game(
        Situation(orders=orders),
        order_geo_info=[_valid(i) for i in range(len(orders))],
        convoy_graph=graph,
    )

    by_field = {order.current: order for order in result.orders}
    assert by_field["Edi"].order == OrderType.hld
    assert by_field["Edi"].dest == "Bel"
    assert by_field["NTH"].dislodged is True
    assert result.pattfields is not None
    assert "Bel" in result.pattfields
