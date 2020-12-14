# std py
from typing import List
# 3rd level
# local
import dipworkpy.model as model
import dipworkpy.dip_eval as dip_eval
from .dip_eval.eval_model import t_world, t_field, t_order

__ALL__ = [ "conflict_game" ]

################################################


def t_order_from_order(o:model.Order) -> t_order:
    OrderType = model.OrderType
    if o.order is None or o.order == OrderType.hld: return t_order.none
    elif o.order == OrderType.mve: return t_order.nmove # cmove/umove may be decided later
    elif o.order == OrderType.sup: return t_order.msupport if o.target else t_order.hsupport
    elif o.order == OrderType.con: return t_order.convoy
    else: raise KeyError(f"unkown OrderType:{o.order} for t_order")


def parser(situation: model.Situation) -> t_world:
    world = t_world(
        fields_={},
        switches=situation.switches)
    # umkremepeln: wir betrachten Felder, die sich gegenseitig angreifen.
    for o in situation.orders:
        if world.get_field(o.current): # schon drin
            raise LookupError(f"fieldname {o.current} twice in current.")
        strength = 1
        field = t_field(
            player = o.nation,
            order = t_order_from_order(o),
            dest = o.target or o.current,
            xref = o.target or o.current,
            strength = strength,
            support_strength = strength,
            defensive_strength = strength,
            name = o.current,
            original_order = None
        )
        if not field.order in { t_order.cmove, t_order.nmove }:
            field.strength_a = strength
            field.strength_b = strength
        # add
        world.set_field(field)
    # result
    return world

################################################


def order_from_t_order(order : t_order):
    if order in { t_order.cmove, t_order.nmove }:
        return model.OrderType.mve
    elif order in { t_order.none, t_order.umove }:
        return model.OrderType.hld
    elif order in { t_order.hsupport, t_order.msupport }:
        return model.OrderType.sup
    elif order in { t_order.convoy }:
        return model.OrderType.con
    else:
        raise ValueError(f"unimplemented t_order:{order}")


def write_results(world : t_world) -> model.ConflictResolution:
    orders : List[model.OrderResult] = []
    for f in world.get_fields():
        orr = model.OrderResult(
                nation=f.player,
                utype=f.original_order.utype if f.original_order else '?',
                current=f.name,
                order=order_from_t_order(f.order),
                target=f.dest, # TODO or xref? or original.dest?
                success=f.succeeds,
                dislodged=f.dislodged,
            )
        orders.append(orr)
    #
    return model.ConflictResolution(orders=orders)


################################################


def conflict_game(situation: model.Situation) -> model.ConflictResolution:
    world = parser(situation)
    dip_eval.k1_evaluation(world)
    dip_eval.k2_evaluation(world)
    dip_eval.k3_evaluation(world)
    dip_eval.k4_evaluation(world)
    dip_eval.k0_evaluation(world)
    return write_results(world)


