# 3rd party

# python
from typing import List, Dict, Set, Optional
from enum import Enum
# 3rd party
from pydantic import BaseModel

########################
# common

class OrderType(str, Enum):
    hld = "hld"
    mve = "mve"
    sup = "sup"
    con = "con"

########################
# requests

class Order(BaseModel):
    nation: str
    utype: str = "A"
    current: str  # current field name
    order: Optional[OrderType] = None   # mve, hld, con, sup
    target: Optional[str] = None  # target field of mve, con, sup

class Switches(BaseModel):
    verbose: Optional[bool] = False

class Situation(BaseModel):
    orders: List[Order] = []
    switches: Optional[Switches] = Switches()


########################
# results

class OrderResult(BaseModel): # could be derived from Order?
    nation: str
    utype: str = "A"
    current: str  # current field name
    order: Optional[OrderType] = None   # mve, hld, con, sup
    target: Optional[str] = None  # target field of mve, con, sup
    success: Optional[bool] # for results
    dislodged: Optional[bool] # for results. retreat or disband


class ConflictResolution(BaseModel):
    orders: List[OrderResult]


class ConflictCheck(BaseModel):
    nations: Set[str]
    utypes: Set[str]
    afields: Set[str]
    orders: Dict[OrderType, int]  # {'hld' : ..., }
    order_errors = int

########################
