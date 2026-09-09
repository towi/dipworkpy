import logging

import dipworkpy.eval as dip_eval_mod
from dipworkpy.conflict_game import conflict_game, parser as conflict_game_parser
from dipworkpy.eval.eval_model import t_order
from dipworkpy.geo_model import ConvoyGraph, OrderGeoInfo
from dipworkpy.model import Order, OrderType, Situation, Switches


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
    # Gilgamesch C.2.1: the dead convoy leaves a single-attacker stand at
    # Bel -- no standoff mark, so Bel is no pattfield.
    assert "Bel" not in result.pattfields


def _cnv_events(field) -> list:
    return [ev for ev in field._events if ev.startswith("$cnv:")]


def test_graph_mode_emits_single_cnv_event_on_cmove() -> None:
    """Graph-mode route resolution leaves exactly one $cnv event on the
    cmove field: the authoritative route check of the FINAL pass emits it,
    and the discarded optimistic/pessimistic passes cannot leak theirs
    (each pass restarts from the deep-copied snapshot)."""
    orders = [
        Order(nation="En", utype="A", current="Edi", order=OrderType.mve, dest="Bel"),
        Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Edi"),
    ]
    graph = ConvoyGraph(
        coastal_edges={("Edi", "NTH"), ("NTH", "Bel")},
        convoyer_fields={"NTH"},
        cmove_candidates={0},
    )

    world = conflict_game_parser(Situation(orders=orders), convoy_graph=graph)
    dip_eval_mod.k1_evaluation(world)

    edi = world.get_field("Edi")
    assert edi.order == t_order.cmove  # active cmove: route alive in both regimes
    assert _cnv_events(edi) == ["$cnv:graph"]


def test_graph_mode_probe_emits_no_cnv_event() -> None:
    """B.3.2.15 probe (6.F.16 Pandin shape, graph edition): the support at
    the cmove's destination attacks the single NECESSARY convoyer, so
    _b3215_protected probes convoy_route_valid WITHOUT that fleet. The
    probe is hypothetical and must not add a $cnv event -- without the
    emit_event=False dedup the final state would carry the probe's
    $cnv:none IN ADDITION to the route check's $cnv:graph."""
    orders = [
        Order(nation="En", utype="F", current="Lon", order=OrderType.msup, dest="Wal"),
        Order(nation="En", utype="F", current="Wal", order=OrderType.mve, dest="ENG"),
        Order(nation="Fr", utype="A", current="Bre", order=OrderType.mve, dest="Lon"),
        Order(nation="Fr", utype="F", current="ENG", order=OrderType.con, dest="Bre"),
        Order(nation="Ge", utype="F", current="Nth", order=OrderType.msup, dest="Bel"),
        Order(nation="Ge", utype="F", current="Bel", order=OrderType.mve, dest="ENG"),
    ]
    graph = ConvoyGraph(
        coastal_edges={("Bre", "ENG"), ("ENG", "Lon")},
        convoyer_fields={"ENG"},
        cmove_candidates={2},
    )

    world = conflict_game_parser(Situation(orders=orders), convoy_graph=graph)
    dip_eval_mod.k1_evaluation(world)

    # the B.3.2.15 protection really fired: the probe scenario is live
    lon = world.get_field("Lon")
    assert "$sup_prot" in lon._events
    bre = world.get_field("Bre")
    assert bre.order == t_order.cmove  # active cmove: route alive in both regimes
    assert _cnv_events(bre) == ["$cnv:graph"]


def test_graph_overrides_engine_switch_with_single_warning(caplog) -> None:
    """Graph AND Switches.convoy_routing_engine both configured: the GRAPH
    wins (the fixed spec routes via ION, which survives -- yet the army
    holds, so the graph's NTH-only route was used) and the override warning
    is logged EXACTLY ONCE per conflict_game run, not once per
    convoy_route_valid call (the 3-pass driver calls it repeatedly)."""
    orders = [
        Order(nation="En", utype="A", current="Edi", order=OrderType.mve, dest="Bel"),
        Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Edi"),
        Order(nation="En", utype="F", current="ION", order=OrderType.con, dest="Edi"),
        Order(nation="Ge", utype="F", current="ENG", order=OrderType.mve, dest="NTH"),
        Order(nation="Ge", utype="F", current="Lon", order=OrderType.msup, dest="ENG"),
    ]
    graph = ConvoyGraph(
        coastal_edges={("Edi", "NTH"), ("NTH", "Bel")},
        convoyer_fields={"NTH", "ION"},
        cmove_candidates={0},
    )
    # contradicts the graph: the fixed engine would route via the surviving ION
    switches = Switches(convoy_routing_engine="fixed:Edi--ION; ION--Bel")

    with caplog.at_level(logging.WARNING, logger="dipworkpy.eval.eval_k1"):
        result = conflict_game(
            Situation(orders=orders, switches=switches),
            order_geo_info=[_valid(i) for i in range(len(orders))],
            convoy_graph=graph,
        )

    by_field = {order.current: order for order in result.orders}
    assert by_field["Edi"].order == OrderType.hld
    assert by_field["Edi"].dest == "Bel"
    assert by_field["NTH"].dislodged is True
    assert result.pattfields is not None
    assert "Bel" not in result.pattfields
    override_warnings = [r for r in caplog.records if "convoy_graph is set" in r.getMessage()]
    assert len(override_warnings) == 1
    assert "ignoring Switches.convoy_routing_engine='fixed:Edi--ION; ION--Bel'" in override_warnings[0].getMessage()


def test_graph_with_default_switches_no_warning(caplog) -> None:
    """'always' is the Switches MODEL DEFAULT, not a deliberate engine
    configuration: a graph-mode run with untouched default switches is the
    normal production path and must NOT log the override warning. Only an
    EXPLICITLY set convoy_routing_engine counts as an override."""
    orders = [
        Order(nation="En", utype="A", current="Edi", order=OrderType.mve, dest="Bel"),
        Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Edi"),
    ]
    graph = ConvoyGraph(
        coastal_edges={("Edi", "NTH"), ("NTH", "Bel")},
        convoyer_fields={"NTH"},
        cmove_candidates={0},
    )
    world = conflict_game_parser(Situation(orders=orders), convoy_graph=graph)  # default switches

    with caplog.at_level(logging.WARNING, logger="dipworkpy.eval.eval_k1"):
        dip_eval_mod.k1_evaluation(world)

    assert world.get_field("Edi").order == t_order.cmove  # graph routing worked
    assert not [r for r in caplog.records if "convoy_graph is set" in r.getMessage()]


def test_fixed_engine_without_graph_no_warning(caplog) -> None:
    """Regression guard: graph-less fixed-engine callers keep their
    $cnv path events and get NO override warning."""
    orders = [
        Order(nation="En", utype="A", current="Edi", order=OrderType.mve, dest="Bel"),
        Order(nation="En", utype="F", current="NTH", order=OrderType.con, dest="Edi"),
    ]
    world = conflict_game_parser(
        Situation(orders=orders, switches=Switches(convoy_routing_engine="fixed:Edi--NTH; NTH--Bel"))
    )

    with caplog.at_level(logging.WARNING, logger="dipworkpy.eval.eval_k1"):
        dip_eval_mod.k1_evaluation(world)

    edi = world.get_field("Edi")
    assert edi.order == t_order.cmove  # route alive
    assert _cnv_events(edi) == ["$cnv:['Edi', 'NTH', 'Bel']"]
    assert not [r for r in caplog.records if "convoy_graph is set" in r.getMessage()]
