"""
Taken in big chunks from DIP_EVAL.pas.
"""

# std py
import itertools
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
# 3rd level
from pydantic import BaseModel
# local
import model

__ALL__ = [ "impl_resolve" ]

##########################################################
# internal model
from src import graphs


class t_order(str, Enum):
    #should not happen the way we store the world:
    # empty = 'empty' # {no unit in this space}
    none = "none" # {hold, irregular, impossible or missing order}
    convoy = "convoy" # {convoy order}
    hsupport = "hsupport" # {order to support a hold order}
    msupport = "msupport" # {order to support a move order}
    nmove = "nmove" # {normal move order}
    cmove = "cmove" # {move per convoy order}
    umove = "umove" # {unsuccessfull move order}

def t_order_from_Order(o:model.Order):
    if o.order == model.OrderType.hld: return t_order.none
    elif o.order == model.OrderType.mve: return t_order.nmove # cmove/umove may be decided later
    elif o.order == model.OrderType.sup: return t_order.msupport if o.target else t_order.hsupport
    elif o.order == model.OrderType.con: return t_order.convoy
    else: raise KeyError(f"unkown OrderType:{o.order} for t_order")


class t_field(BaseModel):
    player: str # nation
    order: t_order
    dest: str # target
    xref: str # same as target for now; TODO: "overfield" of target field (target:SpN, xref:Spa)
    strength: int
    # bookkeeping fields
    name: str
    fcategory: int = 0 # pas: t_category
    category: int = 0 # pas: t_category
    succeeds: bool = True
    strength_a: int = 0
    strength_b: int = 0
    defensive_strength: int = 0
    support_strength: int = 0
    dislodged: bool = False
    original_order: Optional[model.Order] # Optional for tests mainly
    retreat_ok: bool = True
    # logging
    _events : List[str] = []
    def add_event(self, msg):
        self._events.append(msg)


class t_world(BaseModel):
    fields_ : Set[t_field]
    switches : model.Switches
    def get_fields(self, pred=lambda f: True):
        return filter(pred, self.fields_.values())
    def get_field(self, name) -> Optional[t_field]:
        return self.fields_.get(name)
    def set_field(self, field:t_field):
        self.fields_[field.name] = field

debug = True


###########################################################


def init_world(situation: model.Situation) -> t_world:
    world = t_world(
        fields={},
        switches=situation.switches)
    # umkremepeln: wir betrachten Felder, die sich gegenseitig angreifen.
    for o in situation.orders:
        if world.get_field(o.current): # schon drin
            raise LookupError(f"fieldname {o.current} twice in current.")
        strength = 1
        field = t_field(
            player = o.nation,
            order = t_order_from_Order(o.order),
            dest = o.target,
            xref = o.target,
            strength = strength,
            support_strength = strength,
            defensive_strength = strength,
            name = o.current,
            original_order = 0
        )
        if not field.order in { t_order.cmove, t_order.nmove }:
            field.strength_a = strength
            field.strength_b = strength
        # add
        world.set_field(field)
    # result
    return world


###########################################################


def cut_supports(world: t_world, category:int, relevant_moves:Set[t_order]):
    _scok = world.switches.self_cut_ok
    _pcp = world.switches.partial_cut_possible
    #
    for _field in world.get_fields(lambda f: f.order in relevant_moves):
        field : t_field = field
        dest_field = world.get_field(field.dest)
        if not dest_field: continue
        if( # field.order in relevant_moves and
            dest_field.category == category and
            dest_field.order in { t_order.hsupport, t_order.msupport } and
            ((dest_field.player != field.player) or _scok)
        ):
            dest_field.support_strength -= field.strength
            field.add_event('$sup_dec')
            if (dest_field.support_strength <= 0) or (_pcp==0) or (_pcp==2 and field.strength>0):
                dest_field.support_strength = 0
                dest_field.order = t_order.none
                dest_field.add_event('$sup_cut')
            pass
        pass
    return


def count_supporters(world: t_world, category:int):
    # msupports
    for _field in world.get_fields(lambda f: f.category==category and f.order in {t_order.msupport}):
        field : t_field = _field
        j = field.xref
        dest_field = world.get_field(j)
        if not dest_field: continue
        dest_field.strength_a += field.support_strength
        if field.player != dest_field.player:
            dest_field.strength_b += field.strength_b
    # hsupports
    for _field in world.get_fields(lambda f: f.category==category and f.order in {t_order.hsupport}):
        field : t_field = _field
        j = field.xref
        dest_field = world.get_field(j)
        if not dest_field: continue
        dest_field.defensive_strength += field.support_strength
    return


def resolve_conflict_at_field(world : t_world, ffield : t_field):
    _ri93 = t_world.switches.rule_interpretation_IX_3
    if ffield.order in { None, t_order.cmove, t_order.nmove }:
        defval : int = 0
    else:
        defval : int = ffield.defensive_strength
    ffield.add_event("$C") # has conflict
    draw_a : bool = False
    draw_b : bool = False
    maxstrength_a : int = defval
    winner_a : t_field = ffield
    maxstrength_b : int = defval
    winner_b : t_field = ffield
    #
    ifield : t_field
    for ifield in world.get_fields(lambda i: i.order in { t_order.nmove, t_order.cmove }):
        if ifield.dest != ffield.name: continue
        ifield.add_event("$A") # attacks
        draw_a |= ifield.strength_a == maxstrength_a
        if ifield.strength_a > maxstrength_a:
            draw_a = False
            maxstrength_a = ifield.strength_a
            winner_a = ifield
        draw_b |= ifield.strength_b == maxstrength_b
        if ifield.strength_b > maxstrength_b:
            draw_b = False
            maxstrength_b = ifield.strength_b
            winner_b = ifield
        #_ if
    #_ for
    #
    if draw_a:
        winner_a = ffield
    if draw_b:
        winner_b = ffield
    #
    if defval > 0 and ffield.player==winner_a.player:
        winner_a = ffield
    #
    if winner_a != ffield and defval > 0:
        if _ri93 == 0:
            if winner_b == ffield: winner_a = ffield
        elif _ri93 == 1:
            if winner_b != winner_a: winner_a = ffield
        elif _ri93 == 2:
            if winner_a.strength_b <= defval: winner_a = ffield
        else:
            raise NameError(f"unknown rule_interpretation_IX_3:{_ri93}")
    #
    for ifield in world.get_fields(lambda i: i.order in {t_order.nmove, t_order.cmove}):
        if ifield.dest == ffield.name:
            ifield.succeeds = ifield == winner_a
            ifield.add_event("$WIN:%s" % ifield.succeeds)
    #
    return


def change_moves_to_umoves(world : t_world, category:int):
    for field in world.get_fields(
        lambda f:
            f.order in {t_order.cmove, t_order.convoy} and
            f.category == category and
            not f.succeeds
    ):
        field.order = t_order.umove
    return


def _convoy_route_valid_fixed(field:t_field, edges:Set[Tuple[str,str]], convoyer_names:Set[str]):
    start, end = field.name, field.dest
    graph : Dict[str,Set[str]] = graphs.make_graph_from_bi_edges(edges, allowed_nodes=convoyer_names | {start,end})
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


def k1_evaluation(world: t_world):
    if debug: print('=== K1 ===')
    # {mark k1 fields}
    ifield : t_field
    for field in world.get_fields(lambda f: f.order in { t_order.convoy }):
        field.fcategory = 1
        field.add_event('$k1f')
    # {mark k1 moves and supports}
    for field in world.get_fields(lambda f: f.order in { t_order.hsupport, t_order.msupport, t_order.nmove }):
        dest_field = world.get_field(field.dest)
        if dest_field and dest_field.fcategory==1:
            dest_field.category = 1
            field.add_event('$k1c')
    cut_supports(world, category=1, relevant_moves={ t_order.nmove })
    count_supporters(world, category=1)
    # {evaluate conflicts}
    for field in world.get_fields(lambda f: f.category==1):
        resolve_conflict_at_field(world, field)
    change_moves_to_umoves(world, category=1)
    # {evaluate dislodgements of convoyers}
    for field in world.get_fields(lambda f: f.category==1 and f.order in {t_order.nmove}):
        dest_field = world.get_field(field.dest)
        if not dest_field: continue
        dest_field.order = t_order.none
        dest_field.add_event("$cdsl")
    # {check convoy routes}
    for ifield in world.get_fields(lambda f: f.order in {t_order.cmove}):
        my_convoyers = {
            jfield.name
            for jfield in world.get_fields()
            if jfield.order in {t_order.convoy} and jfield.xref == ifield.name
        }
        if not convoy_route_valid(world=world, field=ifield, convoyer_names=my_convoyers):
            ifield.order = t_order.none
            ifield.add_event("$criv") # convoy route invalid
    #
    return


###########################################################


def impl_resolve(situation: model.Situation):
    world = init_world(situation)
    k1_evaluation(world)




