from dipworkpy.model import Order, OrderType
from dipworkpy.syntax.model import SyntaxRequest
from dipworkpy.syntax.service import syntax_phase


def _o(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current,
                 order=OrderType(order) if order else None, dest=dest)


def test_syn_001_strikes_unknown_nation():
    req = SyntaxRequest(
        orders=[_o("ZZ", "A", "Vie", "hld")],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    # struck order replaced by hold-default for Vie
    assert len(resp.orders) == 1
    assert resp.orders[0].nation == "Au"
    assert resp.orders[0].order == OrderType.hld


def test_syn_004_strikes_unknown_current_field():
    req = SyntaxRequest(
        orders=[_o("Au", "A", "ZZZ", "hld")],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    # struck - but Vie still gets a hold-default
    assert any(o.current == "Vie" for o in resp.orders)
    assert not any(o.current == "ZZZ" for o in resp.orders)


def test_syn_005_double_order_strikes_both():
    req = SyntaxRequest(
        orders=[
            _o("Au", "A", "Vie", "hld"),
            _o("Au", "A", "Vie", "mve", "Boh"),
        ],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    # both struck, hold-default injected
    holds = [o for o in resp.orders if o.current == "Vie"]
    assert len(holds) == 1
    assert holds[0].order == OrderType.hld


def test_syn_008_hold_default_for_unordered_unit():
    req = SyntaxRequest(
        orders=[],
        unit_positions={"Vie": ("Au", "A"), "Lon": ("En", "F")},
    )
    resp = syntax_phase(req)
    nations = {o.nation for o in resp.orders}
    assert nations == {"Au", "En"}
    assert all(o.order == OrderType.hld for o in resp.orders)


def test_syn_emits_diagnostics():
    req = SyntaxRequest(
        orders=[_o("ZZ", "A", "Vie", "hld")],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    codes = {d.rule for d in resp.diagnostics}
    assert "SYN-001" in codes
    assert "SYN-008" in codes
