"""
impl k1 phase
"""

# std py
from typing import Dict, Iterable, Set, Tuple, cast
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


def k1_evaluation(world: t_world):
    log = _logger.getChild("k1_evaluation")
    log.info("k1_evaluation")
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
    eval_common.cut_supports(world, category=1, relevant_moves={nmove})
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
    for ifield in world.get_fields(lambda f: f.order in {cmove}):
        my_convoyers = {
            jfield.name for jfield in world.get_fields() if jfield.order in {convoy} and jfield.xref == ifield.name
        }
        if not convoy_route_valid(world=world, field=ifield, convoyer_names=my_convoyers):
            ifield.order = t_order.none
            ifield.add_event("$criv")  # convoy route invalid
            log.debug("k1 invalid convoy route for field:%s via %s", ifield, my_convoyers)
    #
    log.debug("DONE k1. fields: %s", dip_eval_mod.LogList(world.get_fields()))
    return


###########################################################
