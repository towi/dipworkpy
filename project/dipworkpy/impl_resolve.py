# std py
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
# 3rd level
from pydantic import BaseModel
# local
import model
import cfl_resolve
from cfl_resolve.cfl_model import t_world, t_field, t_order, t_order_from_Order

__ALL__ = [ "impl_resolve" ]


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


def impl_resolve(situation: model.Situation):
    world = init_world(situation)
    cfl_resolve.k1_evaluation(world)




