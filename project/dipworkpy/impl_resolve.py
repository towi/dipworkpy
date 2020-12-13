# std py
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
# 3rd level
from pydantic import BaseModel
# local
import model
import dip_eval
from dip_eval.eval_model import t_world, t_field, t_order, t_order_from_Order

__ALL__ = [ "impl_resolve" ]


def parser(situation: model.Situation) -> t_world:
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
            original_order = None
        )
        if not field.order in { t_order.cmove, t_order.nmove }:
            field.strength_a = strength
            field.strength_b = strength
        # add
        world.set_field(field)
    # result
    return world


def write_results(world : t_world) -> model.ConflictResolution:
    return model.ConflictResolution(
        orders=[
            model.OrderResult(
                nation=f.player,
                utype=f.original_order.utype if f.original_order else None,
                current=f.name,
                order=None, # TODO
                target=f.dest, # TODO or xref? or original.dest?
                success=f.succeeds,
                dislodged=f.dislodged,
            )
            for f in world.get_fields() ]
    )


def conflict_game(situation: model.Situation) -> model.ConflictResolution:
    world = parser(situation)
    dip_eval.k1_evaluation(world)
    dip_eval.k2_evaluation(world)
    dip_eval.k3_evaluation(world)
    dip_eval.k4_evaluation(world)
    dip_eval.k5_evaluation(world)
    dip_eval.k0_evaluation(world)
    return write_results(world)


