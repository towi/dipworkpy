"""
impl k1 phase
"""

# std py
from typing import Dict, Set, Tuple
# 3rd level
# local
from eval_model import t_order, t_field, t_world
import eval_common
import dipworkpy.graphs as graphs
from dipworkpy import debug

__ALL__ = [ "k1_evaluation" ]


###########################################################


def _convoy_route_valid_fixed(field:t_field, edges:Set[Tuple[str,str]], convoyer_names:Set[str]):
    start, end = field.name, field.dest
    graph : Dict[str,Set[str]] = graphs.make_graph_from_bi_edges(edges, allowed_nodes=convoyer_names | {start, end})
    path = graphs.find_shortest_path(graph, start=start, end=end)
    field.add_event(f"$cnv:{path}") # show selected convoy route
    return path is not None


# TODO: call an external geographic service
def convoy_route_valid(world:t_world, field:t_field, convoyer_names:Set[str]):
    """field.name to field.dest"""
    _cre : str = world.switches.convoy_routing_engine
    if _cre == "always":
        return len(convoyer_names) > 0
    elif _cre.startswith("fixed:"): # user provided. good for tests
        spec = _cre[len("fixed:"):]  #  python set of pairs: "{ ("a","b"), ("b","c"), ...}"
        edges : Set[Tuple[str,str]] = eval(spec, {}, {})
        return _convoy_route_valid_fixed(field, edges, convoyer_names)
    else:
        raise ValueError(f"unknown convoy_routing_engine:{_cre}")


###########################################################


def k1_evaluation(world: t_world):
    if debug: print('=== K1 ===')
    # prepare
    # - aliases for brevity
    hsupport, msupport, cmove, nmove, umove, convoy = t_order.hsupport, t_order.msupport, t_order.cmove, t_order.nmove, t_order.umove, t_order.convoy
    #
    # {mark k1 fields}
    ifield : t_field
    dest_field : t_field
    for ifield in world.get_fields(lambda f: f.order in { convoy }):
        ifield.fcategory = 1
        ifield.add_event('$k1f')
    #
    # {mark k1 moves and supports}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in { hsupport, msupport, nmove }):
        if dest_field.fcategory == 1:
            dest_field.category = 1
            ifield.add_event('$k1c')
    eval_common.cut_supports(world, category=1, relevant_moves={nmove})
    eval_common.count_supporters(world, category=1)
    #
    # {evaluate conflicts}
    for ifield in world.get_fields(lambda f: f.category==1):
        eval_common.resolve_conflict_at_field(world, ifield)
    eval_common.change_moves_to_umoves(world, category=1)
    #
    # {evaluate dislodgements of convoyers}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.category==1 and f.order in {nmove}):
        dest_field.order = t_order.none
        dest_field.add_event("$cdsl")
    #
    # {check convoy routes}
    for ifield in world.get_fields(lambda f: f.order in {cmove}):
        my_convoyers = {
            jfield.name
            for jfield in world.get_fields()
            if jfield.order in {convoy} and jfield.xref == ifield.name
        }
        if not convoy_route_valid(world=world, field=ifield, convoyer_names=my_convoyers):
            ifield.order = t_order.none
            ifield.add_event("$criv") # convoy route invalid
    #
    return


###########################################################

