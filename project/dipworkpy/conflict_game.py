# std py
from typing import List
from logging import getLogger
# 3rd level
# local
import dipworkpy.model as model
import dipworkpy.dip_eval as dip_eval
from .dip_eval.eval_model import t_world, t_field, t_order, NO_PLAYER

__ALL__ = [ "conflict_game" ]

################################################

_logger = getLogger(__name__)


def t_order_from_order(o:model.Order) -> t_order:
    OrderType = model.OrderType
    if o.order is None or o.order == OrderType.hld: return t_order.none
    elif o.order == OrderType.mve: return t_order.nmove # cmove will be decided later
    elif o.order == OrderType.msup: return t_order.msupport
    elif o.order == OrderType.hsup: return t_order.hsupport
    elif o.order == OrderType.con: return t_order.convoy
    else: raise KeyError(f"unkown OrderType:{o.order} for t_order")


def t_field_from_order(o : model.Order) -> t_field:
    strength = int(o.utype) if o.utype in "1234567890" else 1
    field = t_field(
        player=o.nation,
        order=t_order_from_order(o),
        dest=o.dest or o.current,
        xref=o.dest or o.current,
        strength=strength,
        support_strength=strength,
        defensive_strength=strength,
        name=o.current,
        original_order=o
    )
    if not field.order in {t_order.cmove, t_order.nmove}:
        field.strength_a = strength
        field.strength_b = strength
    return field

empty_field_Order = None

def t_field_empty(name : str) -> t_field:
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
        original_order=empty_field_Order
    )
    return field


def parser(situation: model.Situation) -> t_world:
    log = _logger.getChild("parser")
    world = t_world(
        fields_={},
        switches=situation.switches)
    log.info("parser()")
    log.debug("IN situation.orders: %s", dip_eval.LogList(situation.orders, prefix="\n-o "))
    # umkremepeln: wir betrachten Felder, die sich gegenseitig angreifen.
    for o in situation.orders:
        if world.get_field(o.current):  # schon drin
            raise LookupError(f"fieldname {o.current} twice in current.")
        field = t_field_from_order(o)
        # add
        world.set_field(field)
    # the world representation needs empty explicit empty fields for destinations.
    all_currents = { f.name  for f in world.get_fields() }
    all_dests = { f.dest  for f in world.get_fields() }
    log.debug("adding needed empty destination fields: %s", all_dests - all_currents)
    for dest in all_dests - all_currents:
        world.set_field(t_field_empty(dest))
    # change nmoves to cmoves
    field : t_field
    for field, dest_field in world.get_fields_dests(lambda f: f.order in { t_order.convoy } ):
        if field.order in { t_order.nmove }:
            log.debug("- changing nmove to cmove for field:%s because of dest:%s", field, dest_field)
            field.order = t_order.cmove
            field.add_event("$cmove")
    # result
    log.debug("OUT world.fields: %s", dip_eval.LogList(world.get_fields()))
    return world


################################################


def order_from_t_order(order : t_order):
    if order in { t_order.cmove, t_order.nmove }:
        return model.OrderType.mve
    elif order in { t_order.none, t_order.umove }:
        return model.OrderType.hld
    elif order in { t_order.msupport }:
        return model.OrderType.msup
    elif order in { t_order.hsupport }:
        return model.OrderType.hsup
    elif order in { t_order.convoy }:
        return model.OrderType.con
    else:
        raise ValueError(f"unimplemented t_order:{order}")


def writer(world: t_world) -> model.ConflictResolution:
    log = _logger.getChild("writer")
    orders: List[model.OrderResult] = []
    f: t_field
    log.info("writer()")
    log.debug("IN world.fields: %s", dip_eval.LogList(world.get_fields()))
    # moves
    for f in world.get_fields():
        if f.player == NO_PLAYER:
            continue  # empty fields that were just destinations
        order = order_from_t_order(f.order)
        orr = model.OrderResult(
                nation=f.player,
                utype=f.original_order.utype if f.original_order else '?',
                current=f.name,
                order=order,
                dest=f.dest,  # TODO or xref? or original.dest?
                succeeds=False  if not f.succeeds else None,
                dislodged=True  if f.dislodged else None,
                original=f.original_order
            )
        orders.append(orr)
    # figure out pattfields. TODO: alpha
    efields = { f.name  for f in world.get_fields(lambda f: f.player == NO_PLAYER) }
    ufields = { f.dest  for f in world.get_fields(lambda f: f.order in {t_order.umove}) }
    sfields = { f.dest  for f in world.get_fields(lambda f: f.order in {t_order.nmove, t_order.cmove}) }
    hfields = { f.name  for f in world.get_fields(lambda f: f.order in {t_order.hsupport, t_order.msupport, t_order.none }) }
    # .. (all empty fields and fields with blocked moved) minus (destination of moves) minus (hold fields ignoring empty fields)
    pattfields = (efields | ufields) - sfields - (hfields - efields)
    #
    log.debug("OUT conflict_resolution.orders: %s, ", dip_eval.LogList(orders, prefix="\n-r "))
    log.debug("OUT conflict_resolution.pattfields: %s, ", pattfields)
    return model.ConflictResolution(orders=orders, pattfields=pattfields)


################################################


def conflict_game(situation: model.Situation) -> model.ConflictResolution:
    world = parser(situation)
    dip_eval.k1_evaluation(world)
    dip_eval.k2_evaluation(world)
    dip_eval.k3_evaluation(world)
    dip_eval.k4_evaluation(world)
    dip_eval.k0_evaluation(world)
    return writer(world)


