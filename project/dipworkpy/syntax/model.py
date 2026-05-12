from __future__ import annotations
from typing import Dict, List, Tuple

from pydantic import BaseModel, Field

from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import MapRef
from dipworkpy.model import Order, Switches


class SyntaxRequest(BaseModel):
    orders: List[Order]
    unit_positions: Dict[str, Tuple[str, str]]
    map: MapRef = Field(default_factory=MapRef)
    switches: Switches = Field(default_factory=Switches)


class SyntaxResponse(BaseModel):
    orders: List[Order]
    diagnostics: List[Diagnostic] = Field(default_factory=list)
