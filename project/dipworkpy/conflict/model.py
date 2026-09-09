"""ConflictRequest / ConflictResponse DTOs."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import ConvoyGraph, OrderGeoInfo
from dipworkpy.model import ConflictResolution, Order, Switches


class ConflictRequest(BaseModel):
    orders: List[Order]
    order_geo_info: Optional[List[OrderGeoInfo]] = None
    convoy_graph: Optional[ConvoyGraph] = None
    switches: Switches = Field(default_factory=Switches)


class ConflictResponse(BaseModel):
    resolution: ConflictResolution
    diagnostics: List[Diagnostic] = Field(default_factory=list)
