from dipworkpy.model import Order, OrderType, Switches
from dipworkpy.syntax.model import SyntaxRequest
from dipworkpy.syntax.service import syntax_phase


def _o(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current, order=OrderType(order) if order else None, dest=dest)


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


def test_syn_007_off_by_default_for_std_diplomacy():
    # A fleet on a land field should be allowed when strict_unit_types is off.
    req = SyntaxRequest(
        orders=[_o("Au", "F", "Vie", "hld")],  # Vie is LA, fleet wouldn't fit if strict
        unit_positions={"Vie": ("Au", "F")},
    )
    resp = syntax_phase(req)
    assert any(o.current == "Vie" and o.order == OrderType.hld for o in resp.orders)
    assert not any(d.rule == "SYN-007" for d in resp.diagnostics)


def test_syn_007_strict_unit_types_strikes_army_on_sea():
    req = SyntaxRequest(
        orders=[_o("En", "A", "NTH", "hld")],  # army on sea
        unit_positions={"NTH": ("En", "A")},
        switches=Switches(strict_unit_types=True),
    )
    resp = syntax_phase(req)
    # struck, hold-default re-injected with the same (nation, utype) shape
    syn007 = [d for d in resp.diagnostics if d.rule == "SYN-007"]
    assert len(syn007) == 1


def test_syn_007_strict_unit_types_strikes_fleet_on_inland():
    req = SyntaxRequest(
        orders=[_o("Au", "F", "Vie", "hld")],  # fleet on inland (LA)
        unit_positions={"Vie": ("Au", "F")},
        switches=Switches(strict_unit_types=True),
    )
    resp = syntax_phase(req)
    syn007 = [d for d in resp.diagnostics if d.rule == "SYN-007"]
    assert len(syn007) == 1


def test_syn_emits_diagnostics():
    req = SyntaxRequest(
        orders=[_o("ZZ", "A", "Vie", "hld")],
        unit_positions={"Vie": ("Au", "A")},
    )
    resp = syntax_phase(req)
    codes = {d.rule for d in resp.diagnostics}
    assert "SYN-001" in codes
    assert "SYN-008" in codes
