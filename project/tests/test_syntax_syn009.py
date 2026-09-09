"""SYN-009: ordered unit must belong to the ordering nation; unit type
is advisory and gets corrected from the board."""

from dipworkpy.model import Order, OrderType
from dipworkpy.syntax.model import SyntaxRequest
from dipworkpy.syntax.service import syntax_phase


def test_foreign_unit_order_struck_and_owner_holds():
    req = SyntaxRequest(
        orders=[Order(nation="Ge", utype="F", current="Lon", order=OrderType.mve, dest="NTH")],
        unit_positions={"Lon": ("En", "F")},
    )
    res = syntax_phase(req)
    assert [(o.nation, o.utype, o.current, o.order) for o in res.orders] == [("En", "F", "Lon", OrderType.hld)]
    assert any(d.rule == "SYN-009" for d in res.diagnostics)


def test_wrong_utype_corrected_not_struck():
    req = SyntaxRequest(
        orders=[Order(nation="En", utype="A", current="Lon", order=OrderType.mve, dest="NTH")],
        unit_positions={"Lon": ("En", "F")},
    )
    res = syntax_phase(req)
    assert [(o.nation, o.utype, o.current, o.order, o.dest) for o in res.orders] == [
        ("En", "F", "Lon", OrderType.mve, "NTH")
    ]
    assert any(d.rule == "SYN-009" for d in res.diagnostics)


def test_foreign_order_does_not_double_strike_owners_order():
    """Foreign order + owner's own order on the same unit: SYN-005
    doubles-detection must not count the foreign one, so the owner's
    order survives."""
    req = SyntaxRequest(
        orders=[
            Order(nation="Ge", utype="F", current="Lon", order=OrderType.mve, dest="NTH"),
            Order(nation="En", utype="F", current="Lon", order=OrderType.mve, dest="ENG"),
        ],
        unit_positions={"Lon": ("En", "F")},
    )
    res = syntax_phase(req)
    assert [(o.nation, o.current, o.dest) for o in res.orders] == [("En", "Lon", "ENG")]
