"""
impl k1 phase
"""

# std py
from typing import Dict, Iterable, List, Optional, Set, Tuple, cast
from logging import getLogger

# 3rd level
# local
from .eval_model import t_order, t_field, t_world
import dipworkpy.eval as dip_eval_mod
import dipworkpy.eval.eval_common as eval_common
import dipworkpy.graphs as graphs
from dipworkpy.geo_model import ConvoyGraph
from dipworkpy.geography.convoy import convoy_route_exists

__ALL__ = ["k1_evaluation"]


###########################################################

_logger = getLogger(__name__)


def _convoy_route_valid_fixed(field: t_field, edges: Set[Tuple[str, str]], convoyer_names: Set[str]):
    start, end = field.name, field.dest
    graph = graphs.make_graph_from_bi_edges(edges, allowed_nodes=convoyer_names | {start, end})
    path = graphs.find_shortest_path(cast(Dict[str, Iterable[str]], graph), start=start, end=end)
    field.add_event(f"$cnv:{path}")  # show selected convoy route
    return path is not None


def parse_edges(spec: str, item_sep=";", edge_sep="--") -> Set[Tuple[str, str]]:
    """spec ist angelehnt an die dot-notation von graphviz. also zb: Vie -- Mun; Kie -- NTH;"""
    items = spec.split(item_sep)
    edges = [item.split(edge_sep, 1) for item in items if item.strip()]
    return {(f1.strip(), f2.strip()) for f1, f2 in edges}  # may raise on format error


def _restrict_convoy_graph(graph: ConvoyGraph, convoyer_names: Set[str]) -> ConvoyGraph:
    return ConvoyGraph(
        sea_edges={edge for edge in graph.sea_edges if edge[0] in convoyer_names and edge[1] in convoyer_names},
        coastal_edges={
            edge for edge in graph.coastal_edges if (edge[0] in convoyer_names) != (edge[1] in convoyer_names)
        },
        convoyer_fields=convoyer_names,
        cmove_candidates=graph.cmove_candidates,
    )


def convoy_route_valid(world: t_world, field: t_field, convoyer_names: Set[str]):
    """field.name to field.dest"""
    if world.convoy_graph is not None:
        graph = _restrict_convoy_graph(world.convoy_graph, convoyer_names)
        return convoy_route_exists(field.name, field.dest, graph)

    _cre: str = world.switches.convoy_routing_engine or "always"
    if _cre == "always":
        return len(convoyer_names) > 0
    elif _cre.startswith("fixed:"):  # user provided. good for tests
        spec = _cre[len("fixed:") :]  # simple syntax: "Vie--Mun; Kie -- NTH; "
        edges: Set[Tuple[str, str]] = parse_edges(spec)
        return _convoy_route_valid_fixed(field, edges, convoyer_names)
    else:
        raise ValueError(f"unknown convoy_routing_engine:{_cre}")


###########################################################


def _convoyers_of(world: t_world, cmove_field: t_field) -> Set[str]:
    """Names of the fields with a con order convoying `cmove_field` (con.xref = the convoyed army)."""
    return {
        jfield.name
        for jfield in world.get_fields()
        if jfield.order == t_order.convoy and jfield.xref == cmove_field.name
    }


def _b3215_protected(world: t_world, cmove_field: t_field, sup_field: t_field, convoyers: Set[str]) -> bool:
    """Gilgamesch B.3.2.15 (literal): a move per convoy does not reduce the
    support strength of a unit at the convoy's DESTINATION field when that
    support is used FOR AN ATTACK ON a fleet that is NECESSARY for THIS
    convoy -- necessary = no route survives without it (convoy_route_valid
    with the remaining convoyers). Only move-supports count: a HOLD-support
    of a necessary convoyer is "fürs Halten", not "für einen Angriff", so it
    stays cuttable. The resulting circularity (DATC 6.F.18 betrayal: cut ->
    convoyer dislodged -> route dead -> cut void) has no consistent
    resolution and is handled by the footnote-6 ambiguity fallback in the
    3-pass driver instead."""
    if sup_field.order != t_order.msupport:
        return False
    tgt = sup_field.dest  # msup: the supported move's destination (parser-fixed)
    for f in convoyers:
        if f == tgt and not convoy_route_valid(world=world, field=cmove_field, convoyer_names=convoyers - {f}):
            return True
    return False


def _cmove_cut_supports(world: t_world, allowed: Set[str]) -> None:
    """EXPLICIT cmove cuts of category-1 supports (the convoy layer), B.3.2.15-filtered.

    The engine never cut a category-1 support before: its category can never be
    re-marked to 4 (a category-1 field targets a convoyer field, and convoyer
    fields keep fcategory 1), so k4's cut_supports always skipped it. That got
    the B.3.2.15-protected paradox cases right by accident but also suppressed
    the LEGITIMATE cuts (DATC 6.F.19/6.F.20). The cut belongs HERE, before the
    convoyer-field resolution, and must not apply to route-dead convoys
    (DATC 6.F.6/6.F.14) -- the 3-pass driver guarantees that by only letting
    `allowed` (route-surviving, unambiguous) cmoves cut.
    """
    _scok: bool = world.switches.self_cut_ok or False
    _pcp: int = world.switches.partial_cut_possible or 0
    for cmove_field in world.get_fields(lambda f: f.order == t_order.cmove and f.name in allowed):
        dest_field = world.get_field(cmove_field.dest)
        if not dest_field:
            continue
        if not (
            dest_field.category == 1
            and dest_field.order in {t_order.hsupport, t_order.msupport}
            and ((dest_field.player != cmove_field.player) or _scok)
        ):
            continue
        convoyers = _convoyers_of(world, cmove_field)
        if _b3215_protected(world, cmove_field, dest_field, convoyers):
            dest_field.cut_protected = True  # durable: cut_supports skips it in k2-k4 ($sup_prot)
            dest_field.add_event("$sup_prot")
            continue
        # apply the cut exactly like eval_common.cut_supports does
        dest_field.support_strength -= cmove_field.strength
        cmove_field.add_event("$sup_dec")
        if (dest_field.support_strength <= 0) or (_pcp == 0) or (_pcp == 2 and cmove_field.strength > 0):
            dest_field.support_strength = 0
            dest_field.order = t_order.none
            dest_field.succeeds = False
            dest_field.add_event("$sup_cut")


def _k1_pass(world: t_world, regime: str, active: Optional[Set[str]] = None) -> Dict[str, bool]:
    """One k1 evaluation pass (the original k1 logic plus regime handling).

    regime:
    - 'optimistic': every B.3.2.15-permitted cmove cut applied; cmoves move.
    - 'pessimistic': NO cmove cuts at all, but cmoves still move/bounce
      normally (only the cut step is suppressed).
    - 'final': only `active` cmoves cut and move; every other cmove stands
      ($fn6 pre-demotion -- Gilgamesch B.3.2.15 footnote 6: ambiguous units
      stand and their cuts are void; route-dead-in-both-regimes units fail
      their convoy anyway).
    Returns {cmove name: convoy route survives} (post-dislodgement).
    """
    log = _logger.getChild("_k1_pass")
    log.info("_k1_pass regime:%s active:%s", regime, sorted(active or set()))
    # prepare
    # - aliases for brevity
    hsupport, msupport, cmove, nmove, convoy = (
        t_order.hsupport,
        t_order.msupport,
        t_order.cmove,
        t_order.nmove,
        t_order.convoy,
    )
    #
    # {mark k1 fields}
    ifield: t_field
    dest_field: t_field
    for ifield in world.get_fields(lambda f: f.order in {convoy}):
        ifield.fcategory = 1
        ifield.add_event("$k1f")
    #
    # {mark k1 moves and supports}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in {hsupport, msupport, nmove}):
        if dest_field.fcategory == 1:
            ifield.category = 1
            ifield.add_event("$k1c")
    log.debug(
        "k1 moves and support marks. fields: %s", dip_eval_mod.LogList(world.get_fields(lambda f: f.category == 1))
    )
    #
    cmoves: List[t_field] = list(world.get_fields(lambda f: f.order == cmove))
    routes: Dict[str, bool] = {f.name: False for f in cmoves}
    if regime == "final":
        # fn6 pre-demotion: inactive (ambiguous or route-dead-in-both) cmoves
        # stand -- no move, no cut.
        for ifield in cmoves:
            if ifield.name not in (active or set()):
                ifield.order = t_order.none
                ifield.add_event("$fn6")
                log.debug("k1 fn6: inactive cmove stands: %s", ifield.__log__())
    #
    eval_common.cut_supports(world, category=1, relevant_moves={nmove})
    if regime in {"optimistic", "final"}:
        _cmove_cut_supports(world, allowed={f.name for f in cmoves} if regime == "optimistic" else (active or set()))
    eval_common.count_supporters(world, category=1)
    log.debug("k1 cuts and supports. fields: %s", dip_eval_mod.LogList(world.get_fields(lambda f: f.category == 1)))
    #
    # {evaluate conflicts}
    # Resolve at the convoyer fields (fcategory==1), i.e. the fields actually
    # being contested -- mirroring k2 (fcategory==2) and k4 (fcategory==4).
    # Resolving at the attacker fields (category==1) never contests the
    # attacker's own field, so its `succeeds` kept the default True and every
    # attacked convoyer was demoted unconditionally (DipNet convoyer-dislodge
    # FAIL family, Task 9).
    for ifield in world.get_fields(lambda f: f.fcategory == 1):
        eval_common.resolve_conflict_at_field(world, ifield)
    eval_common.change_moves_to_umoves(world, category=1)
    #
    # {evaluate dislodgements of convoyers}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.category == 1 and f.order in {nmove}):
        dest_field.order = t_order.none
        dest_field.add_event("$cdsl")
        log.debug("k1 blocked dislodged convoyer field:%s because of %s", dest_field, ifield)
    #
    # {check convoy routes}
    for ifield in world.get_fields(lambda f: f.order == cmove):
        my_convoyers = _convoyers_of(world, ifield)
        if not convoy_route_valid(world=world, field=ifield, convoyer_names=my_convoyers):
            ifield.order = t_order.none
            ifield.add_event("$criv")  # convoy route invalid
            log.debug("k1 invalid convoy route for field:%s via %s", ifield, my_convoyers)
        else:
            routes[ifield.name] = True
    return routes


def k1_evaluation(world: t_world):
    log = _logger.getChild("k1_evaluation")
    log.info("k1_evaluation")
    if not any(f.order == t_order.cmove for f in world.get_fields()):
        # fast path: no convoyed move -> the final pass IS the plain single pass
        _k1_pass(world, "final", active=set())
        log.debug("DONE k1. fields: %s", dip_eval_mod.LogList(world.get_fields()))
        return
    #
    # Gilgamesch B.3.2.15 + footnote 6: three bounded, deterministic passes.
    # (1) optimistic -- every B.3.2.15-permitted cmove cut applied,
    # (2) pessimistic -- no cmove cuts at all.
    # A cmove whose convoy route survives in BOTH regimes cuts and moves;
    # one whose route dies in both regimes just fails; a DIVERGENT one is
    # ambiguous (footnote 6) -> it stands and its cuts are void.
    snapshot: Dict[str, t_field] = {k: f.model_copy(deep=True) for k, f in world.fields_.items()}

    def _restore() -> None:
        world.fields_ = {k: f.model_copy(deep=True) for k, f in snapshot.items()}

    routes_opt = _k1_pass(world, "optimistic")
    _restore()
    routes_pes = _k1_pass(world, "pessimistic")
    _restore()
    active = {name for name, ok in routes_opt.items() if ok and routes_pes.get(name, False)}
    #
    # (3) final pass with the decided active set. Monotonicity caveat: an
    # active cmove's route can still die in the final pass (the voided cuts
    # of OTHER, ambiguous cmoves can restore supports that then dislodge a
    # convoyer -- the cut set of the final pass is a subset of optimistic,
    # but restored supports are NOT a subset of the pessimistic state). If
    # that happens the cmove stands after all: drop it from the active set
    # and re-run -- bounded at 3 final-pass iterations.
    for _iteration in range(3):
        if _iteration > 0:
            _restore()
        routes_fin = _k1_pass(world, "final", active=active)
        dead = {name for name in active if not routes_fin.get(name, False)}
        if not dead:
            break
        log.warning("k1 final pass unstable; active cmoves lost their route: %s", sorted(dead))
        active -= dead
    else:
        log.warning("k1 final pass did not stabilize within 3 iterations; accepting last state")
    log.debug("DONE k1. fields: %s", dip_eval_mod.LogList(world.get_fields()))
    return


###########################################################
