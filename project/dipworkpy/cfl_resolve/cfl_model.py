"""
conflitcter internal model
"""

# std py
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum
# 3rd level
from pydantic import BaseModel
# local
import dipworkpy.model as model

##########################################################
# internal model


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




