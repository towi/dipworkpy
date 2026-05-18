"""Geography-service request/response DTOs."""

from __future__ import annotations

from typing import List, Set

from pydantic import BaseModel, Field

from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import ConvoyGraph, MapRef, OrderGeoInfo
from dipworkpy.model import Order


class GeographyRequest(BaseModel):
    orders: List[Order]
    map: MapRef = Field(default_factory=MapRef)


class GeographyResponse(BaseModel):
    orders: List[Order]
    order_geo_info: List[OrderGeoInfo] = Field(default_factory=list)
    convoy_graph: ConvoyGraph = Field(default_factory=ConvoyGraph)
    diagnostics: List[Diagnostic] = Field(default_factory=list)


class RetreatOptionsRequest(BaseModel):
    field: str
    attacked_from: str
    utype: str = "A"
    occupied_fields: Set[str] = Field(default_factory=set)
    map: MapRef = Field(default_factory=MapRef)


class RetreatOptionsResponse(BaseModel):
    field: str
    attacked_from: str
    candidates: List[str]
