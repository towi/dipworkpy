"""round_full — chains syntax -> geography -> conflict."""
from __future__ import annotations

from typing import Dict, List, Tuple

from pydantic import BaseModel, Field

from dipworkpy.conflict.model import ConflictResponse
from dipworkpy.conflict_game import conflict_game
from dipworkpy.diag import Diagnostic
from dipworkpy.geo_model import MapRef
from dipworkpy.geography.model import GeographyRequest, GeographyResponse
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, Situation, Switches
from dipworkpy.syntax.model import SyntaxRequest, SyntaxResponse
from dipworkpy.syntax.service import syntax_phase


class RoundRequest(BaseModel):
    orders: List[Order]
    unit_positions: Dict[str, Tuple[str, str]]
    map: MapRef = Field(default_factory=MapRef)
    switches: Switches = Field(default_factory=Switches)


class RoundResult(BaseModel):
    syntax: SyntaxResponse
    geography: GeographyResponse
    conflict: ConflictResponse
    diagnostics: List[Diagnostic] = Field(default_factory=list)


def round_full(req: RoundRequest) -> RoundResult:
    syn = syntax_phase(SyntaxRequest(
        orders=req.orders, unit_positions=req.unit_positions,
        map=req.map, switches=req.switches,
    ))
    geo = geography_phase(GeographyRequest(orders=syn.orders, map=req.map))
    resolution = conflict_game(
        situation=Situation(orders=geo.orders, switches=req.switches),
        order_geo_info=geo.order_geo_info,
    )
    cnf = ConflictResponse(resolution=resolution)
    return RoundResult(
        syntax=syn, geography=geo, conflict=cnf,
        diagnostics=syn.diagnostics + geo.diagnostics + cnf.diagnostics,
    )
