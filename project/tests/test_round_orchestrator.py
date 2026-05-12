from dipworkpy.model import Order, OrderType
from dipworkpy.round.orchestrator import round_full, RoundRequest


def test_full_round_passes_through_phases():
    req = RoundRequest(
        orders=[Order(nation="Au", utype="A", current="Vie",
                      order=OrderType.mve, dest="Boh")],
        unit_positions={"Vie": ("Au", "A")},
    )
    res = round_full(req)
    assert res.syntax is not None
    assert res.geography is not None
    assert res.conflict is not None
    assert len(res.diagnostics) > 0
