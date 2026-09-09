# std py
from typing import List, Optional, Set
from logging import getLogger

# 3rd level
# local
import dipworkpy.model as model
import dipworkpy.eval as dip_eval_mod
from .eval.eval_model import t_world, t_field, t_order, NO_PLAYER
from .geo_model import ConvoyGraph, OrderGeoInfo

__ALL__ = ["conflict_game"]

################################################

_logger = getLogger(__name__)


def t_order_from_order(o: model.Order) -> t_order:
    OrderType = model.OrderType
    if o.order is None or o.order == OrderType.hld:
        return t_order.none
    elif o.order == OrderType.mve:
        return t_order.nmove  # cmove will be decided later
    elif o.order == OrderType.msup:
        return t_order.msupport
    elif o.order == OrderType.hsup:
        return t_order.hsupport
    elif o.order == OrderType.con:
        return t_order.convoy
    else:
        raise KeyError(f"unkown OrderType:{o.order} for t_order")


def t_field_from_order(o: model.Order, geo: Optional[OrderGeoInfo] = None) -> t_field:
    strength = int(o.utype) if o.utype in "1234567890" else 1
    # Determine initial t_order based on geo classification (B.4.2.9/B.4.2.10).
    # geo is None -> backward-compatible behavior using o.order directly.
    succeeds = True
    if geo is None or geo.effective_behavior == "moves":
        torder = t_order_from_order(o)
        defensive_strength = strength
    elif geo.effective_behavior == "holds_no_support":
        # invalid mve per B.4.2.9 -> failed-move state, NOT hold-supportable.
        # defensive_strength=0 mirrors the standard treatment of a "moving"
        # unit in resolve_conflict_at_field (defval=0 for nmove/cmove): the
        # unit can be displaced like a mid-flight mover. The hsup skip in
        # eval_common.count_supporters keeps it that way through k4.
        torder = t_order.umove
        defensive_strength = 0
        # B.4.2.9 orders have no effect -- the writer must report failure
        # (DipNet 'void' -> (False, None)). Algorithmic umoves (bounces) get
        # their succeeds=False from resolve; only the geo branch needs it here.
        succeeds = False
    elif geo.effective_behavior in ("holds_supportable", "holds_explicit"):
        # invalid hld/sup/con per B.4.2.10 -> regular hold, IS hold-supportable
        torder = t_order.none
        defensive_strength = strength
    else:
        torder = t_order_from_order(o)
        defensive_strength = strength

    field = t_field(
        player=o.nation,
        order=torder,
        dest=o.dest or o.current,
        xref=o.dest or o.current,
        strength=strength,
        support_strength=strength,
        defensive_strength=defensive_strength,
        succeeds=succeeds,
        name=o.current,
        original_order=o,
    )
    if field.order in {t_order.cmove, t_order.nmove}:
        field.strength_a = strength
        field.strength_b = strength
    return field


empty_field_Order = None


def t_field_empty(name: str) -> t_field:
    field = t_field(
        player=NO_PLAYER,
        order=t_order.none,
        dest=name,
        xref=name,
        strength=0,
        strength_a=0,
        strength_b=0,
        support_strength=0,
        defensive_strength=0,
        name=name,
        original_order=empty_field_Order,
    )
    return field


def parser(
    situation: model.Situation,
    order_geo_info: Optional[List[OrderGeoInfo]] = None,
    convoy_graph: Optional[ConvoyGraph] = None,
) -> t_world:
    log = _logger.getChild("parser")
    world = t_world(fields_={}, switches=situation.switches or model.Switches(), convoy_graph=convoy_graph)
    log.info("parser()")
    log.debug("IN situation.orders: %s", dip_eval_mod.LogList(situation.orders, prefix="\n-o "))
    # Build an index for fast lookup; if absent, t_field_from_order uses o.order directly.
    geo_by_index = {g.order_index: g for g in (order_geo_info or [])}
    # umkremepeln: wir betrachten Felder, die sich gegenseitig angreifen.
    for i, o in enumerate(situation.orders):
        if world.get_field(o.current):  # schon drin
            raise LookupError(f"fieldname {o.current} twice in current.")
        field = t_field_from_order(o, geo_by_index.get(i))
        # add
        world.set_field(field)
    # the world representation needs empty explicit empty fields for destinations.
    all_currents = {f.name for f in world.get_fields()}
    all_dests = {f.dest for f in world.get_fields()}
    log.debug("adding needed empty destination fields: %s", all_dests - all_currents)
    for dest in all_dests - all_currents:
        world.set_field(t_field_empty(dest))
    # change nmoves to cmoves.
    # Single source of truth: geography's GEO-009 classification
    # (convoy_graph.cmove_candidates) plus the explicit GEO-010 flag
    # (Order.via_convoy). Without a graph (legacy callers), the raw
    # con-order scan remains as fallback for unflagged orders.
    cmove_idx: Set[int] = set(convoy_graph.cmove_candidates) if convoy_graph is not None else set()
    for i, o in enumerate(situation.orders):
        if i in cmove_idx or o.via_convoy:
            cmove_field = world.get_field(o.current)
            if cmove_field and cmove_field.order in {t_order.nmove}:
                log.debug("- changing nmove to cmove for field:%s (candidates/via_convoy)", cmove_field)
                cmove_field.order = t_order.cmove
                cmove_field.add_event("$cmove")
    if convoy_graph is None:
        for convoy_field, dest_field in world.get_fields_dests(lambda f: f.order in {t_order.convoy}):
            if dest_field.order in {t_order.nmove}:
                log.debug("- changing nmove to cmove for field:%s because of dest:%s", dest_field, convoy_field)
                dest_field.order = t_order.cmove
                dest_field.add_event("$cmove")
    # fix msupport dest: must point to the destination of the supported move
    # (xref stays as the supported unit's location, used by count_supporters)
    for field in world.get_fields(lambda f: f.order in {t_order.msupport}):
        supported = world.get_field(field.xref)
        if supported:
            field.dest = supported.dest
    # result
    log.debug("OUT world.fields: %s", dip_eval_mod.LogList(world.get_fields()))
    return world


################################################


def order_from_t_order(order: t_order):
    if order in {t_order.cmove, t_order.nmove}:
        return model.OrderType.mve
    elif order in {t_order.none, t_order.umove}:
        return model.OrderType.hld
    elif order in {t_order.msupport}:
        return model.OrderType.msup
    elif order in {t_order.hsupport}:
        return model.OrderType.hsup
    elif order in {t_order.convoy}:
        return model.OrderType.con
    else:
        raise ValueError(f"unimplemented t_order:{order}")


def writer(world: t_world) -> model.ConflictResolution:
    log = _logger.getChild("writer")
    orders: List[model.OrderResult] = []
    f: t_field
    log.info("writer()")
    log.debug("IN world.fields: %s", dip_eval_mod.LogList(world.get_fields()))
    # compute dislodgements: a unit is dislodged when a successful move
    # targets its field and the unit didn't move out successfully.
    for f in world.get_fields(lambda f: f.order in {t_order.nmove, t_order.cmove} and f.succeeds):
        dest = world.get_field(f.dest)
        if dest and dest.player != NO_PLAYER:
            # destination has a unit — is it still there?
            if dest.order not in {t_order.nmove, t_order.cmove} or not dest.succeeds:
                dest.dislodged = True
    # moves
    for f in world.get_fields():
        if f.player == NO_PLAYER:
            continue  # empty fields that were just destinations
        order = order_from_t_order(f.order)
        orr = model.OrderResult(
            nation=f.player,
            utype=f.original_order.utype if f.original_order else "?",
            current=f.name,
            order=order,
            dest=f.original_order.dest if f.original_order and f.original_order.dest else f.dest,
            succeeds=False if not f.succeeds else None,
            dislodged=True if f.dislodged else None,
            original=f.original_order,
        )
        # Bucket C: convoy orders report failure only for a SURVIVING fleet of
        # a broken chain (DipNet "no convoy"). A dislodged convoyer is reported
        # via the dislodged flag alone (DipNet R2); a convoyed army that bounced
        # at its destination still means the convoy ran (DipNet R1).
        if f.original_order and f.original_order.order == model.OrderType.con:
            army = world.get_field(f.xref)
            if f.dislodged:
                orr.succeeds = None  # R2: DipNet reports dislodged only
            else:
                executed = army is not None and army.order == t_order.cmove and army.succeeds
                contested = army is not None and army.order == t_order.umove  # R1: convoy ran, army bounced at dest
                orr.succeeds = None if (f.order == t_order.convoy and (executed or contested)) else False
        orders.append(orr)
    # Pattfields (C.3.1.3.2): fields with a movement-phase standoff
    # (C.2.2 beleaguered / multi-attacker tie, C.2.3.1 head-to-head tie).
    # Single-attacker bounces are NOT patt (C.2.1) and never block retreats
    # beyond being occupied/contested.
    pattfields = {f.name for f in world.get_fields(lambda f: f.patt)}
    #
    log.debug("OUT conflict_resolution.orders: %s, ", dip_eval_mod.LogList(orders, prefix="\n-r "))
    log.debug("OUT conflict_resolution.pattfields: %s, ", pattfields)
    return model.ConflictResolution(orders=orders, pattfields=pattfields)


################################################


def conflict_game(
    situation: model.Situation,
    order_geo_info: Optional[List[OrderGeoInfo]] = None,
    convoy_graph: Optional[ConvoyGraph] = None,
) -> model.ConflictResolution:
    world = parser(situation, order_geo_info=order_geo_info, convoy_graph=convoy_graph)
    dip_eval_mod.k1_evaluation(world)
    dip_eval_mod.k2_evaluation(world)
    dip_eval_mod.k3_evaluation(world)
    dip_eval_mod.k4_evaluation(world)
    dip_eval_mod.k0_evaluation(world)
    return writer(world)
