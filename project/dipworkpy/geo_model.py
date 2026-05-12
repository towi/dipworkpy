"""Shared geographic data types.

These types are the interface contract between geography/, syntax/, and
conflict/ services. None of them carries behavior - they are pure data.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Literal, Optional, Set, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field


class FieldType(str, Enum):
    """Field-type classification, mirroring the FIELDS-spec tags."""
    LA  = "LA"
    LCB = "LCB"
    LCA = "LCA"
    LC  = "LC"
    LCF = "LCF"
    L   = "L"
    O   = "O"  # noqa: E741  (Ozean - matches FIELDS spec tag)
    COL = "COL"


class Passable(str, Enum):
    """Passability values for a directed map edge.

    Per the FIELDS spec, an edge has three independent passability values
    (army, fleet, convoy_move). 'imp' marks an unreachable-without-coast
    case; a literal subfield name (e.g. 'SpN') marks a coast-required move.
    """
    YES = "ja"
    NO  = "nein"
    NA  = "-"
    IMP = "imp"


class Edge(BaseModel):
    """A directed map edge with separate passability per unit kind.

    `army` and `fleet` may carry a literal subfield-name string instead of
    a Passable value, indicating the move must specify that coast.
    """
    army: Union[Passable, str]
    fleet: Union[Passable, str]
    convoy_move: Passable


class FieldDef(BaseModel):
    """Definition of a single field."""
    name: str
    type: FieldType
    sub_of: Optional[str] = None
    is_supply_center: bool = False
    home_of: Optional[str] = None
    pos: Optional[Tuple[float, float]] = None


class MapDefinition(BaseModel):
    """A complete map definition - the inline-map shape passed in MapRef."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    fields: Dict[str, FieldDef] = Field(default_factory=dict)
    edges: Dict[Tuple[str, str], Edge] = Field(default_factory=dict)


class MapRef(BaseModel):
    """Reference to a map: either registered map_id or inline definition."""
    map_id: Optional[str] = "standard"
    inline_map: Optional[MapDefinition] = None


class OrderGeoInfo(BaseModel):
    """Per-order classification produced by the Geography service.

    Travels alongside the orders list to the Conflict Resolver. Indexed by
    order position in the parallel orders list.
    """
    order_index: int
    is_valid: bool
    invalidity_code: Optional[str] = None
    invalidity_reason: Optional[str] = None
    effective_behavior: Literal[
        "moves",
        "holds_no_support",
        "holds_supportable",
        "holds_explicit",
    ]
    resolved_coast: Optional[str] = None
    is_convoy_move: bool = False
    explicit_via_convoy: bool = False


class ConvoyGraph(BaseModel):
    """Pre-extracted convoy-relevant subgraph.

    The Conflict Resolver does its own BFS on this graph; Geography only
    delivers the topology and the convoyer set.
    """
    sea_edges: Set[Tuple[str, str]] = Field(default_factory=set)
    coastal_edges: Set[Tuple[str, str]] = Field(default_factory=set)
    convoyer_fields: Set[str] = Field(default_factory=set)
    cmove_candidates: Set[int] = Field(default_factory=set)
