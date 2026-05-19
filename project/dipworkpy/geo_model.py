"""Shared geographic data types.

These types are the interface contract between geography/, syntax/, and
conflict/ services. None of them carries behavior - they are pure data.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


class FieldType(str, Enum):
    """Field-type classification, mirroring the FIELDS-spec tags."""

    LA = "LA"
    LCB = "LCB"
    LCA = "LCA"
    LC = "LC"
    LCF = "LCF"
    L = "L"
    O = "O"  # noqa: E741  (Ozean - matches FIELDS spec tag)
    COL = "COL"


class Passable(str, Enum):
    """Passability values for a directed map edge.

    Per the FIELDS spec, an edge has three independent passability values
    (army, fleet, convoy_move). 'imp' marks an unreachable-without-coast
    case; a literal subfield name (e.g. 'SpN') marks a coast-required move.
    """

    YES = "ja"
    NO = "nein"
    NA = "-"
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

    name: str = ""
    type: FieldType
    sub_of: Optional[str] = None
    is_supply_center: bool = False
    home_of: Optional[str] = None
    pos: Optional[Tuple[float, float]] = None
    features: List[str] = Field(default_factory=list)
    can_build: List[str] = Field(default_factory=list)
    subfields: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    supply_center_value: int = 0
    borders: Dict[str, List[str]] = Field(default_factory=dict)
    diversions: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    neighbor_order: List[str] = Field(default_factory=list)


class MapDefinition(BaseModel):
    """A complete map definition - the inline-map shape passed in MapRef.

    Edges are kept internally as ``(from, to)`` tuples. The preferred JSON/API
    representation is an ordered list of edge objects so border order can be
    preserved for retreat rules. Legacy ``"from:to"`` mappings are still accepted.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    fields: Dict[str, FieldDef] = Field(default_factory=dict)
    edges: Dict[Tuple[str, str], Edge] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _derive_edges_from_borders(self) -> "MapDefinition":
        for name, field in self.fields.items():
            if not field.name:
                field.name = name
        if self.edges:
            return self
        for frm, field in self.fields.items():
            for to, units in field.borders.items():
                self.edges[(frm, to)] = Edge(
                    army=Passable.YES if "A" in units else Passable.NO,
                    fleet=Passable.YES if "F" in units else Passable.NO,
                    convoy_move=Passable.YES if "$convoy" in units else Passable.NO,
                )
        return self

    @field_validator("edges", mode="before")
    @classmethod
    def _parse_json_edge_keys(cls, value: Any) -> Any:
        if isinstance(value, list):
            parsed_list: Dict[Tuple[str, str], Any] = {}
            for item in value:
                if not isinstance(item, dict):
                    return value
                frm = item.get("from")
                to = item.get("to")
                if not isinstance(frm, str) or not isinstance(to, str):
                    return value
                parsed_list[(frm, to)] = {
                    "army": item.get("army"),
                    "fleet": item.get("fleet"),
                    "convoy_move": item.get("convoy_move"),
                }
            return parsed_list
        if isinstance(value, dict):
            parsed: Dict[Tuple[str, str], Any] = {}
            for key, edge in value.items():
                if isinstance(key, tuple):
                    parsed[key] = edge
                    continue
                if isinstance(key, str) and ":" in key:
                    frm, to = key.split(":", 1)
                    parsed[(frm, to)] = edge
                    continue
                parsed[key] = edge
            return parsed
        return value

    @field_serializer("edges", when_used="json")
    def _serialize_json_edge_keys(
        self,
        value: Dict[Tuple[str, str], Edge],
    ) -> list[dict[str, Any]]:
        return [
            {
                "from": frm,
                "to": to,
                "army": edge.army,
                "fleet": edge.fleet,
                "convoy_move": edge.convoy_move,
            }
            for (frm, to), edge in value.items()
        ]


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
    # GEO-010 (Gilgamesch B.3.2.14 explicit `mve [Convoy]` flag) is reserved
    # for a future iteration. The field used to live here as a placeholder;
    # it was never written or read, so it has been removed to avoid hinting
    # at semantics the engine does not provide. When GEO-010 is implemented
    # it will return alongside an Order.via_convoy input field.


class ConvoyGraph(BaseModel):
    """Pre-extracted convoy-relevant subgraph.

    The Python model keeps edge tuples for graph algorithms. JSON uses
    ``"from:to"`` strings so API payloads and saved graph fixtures stay easy
    to review by hand.
    """

    sea_edges: Set[Tuple[str, str]] = Field(default_factory=set)
    coastal_edges: Set[Tuple[str, str]] = Field(default_factory=set)
    convoyer_fields: Set[str] = Field(default_factory=set)
    cmove_candidates: Set[int] = Field(default_factory=set)

    @field_validator("sea_edges", "coastal_edges", mode="before")
    @classmethod
    def _parse_json_graph_edges(cls, value: Any) -> Any:
        if not isinstance(value, (set, list, tuple)):
            return value
        parsed = set()
        for edge in value:
            if isinstance(edge, str) and ":" in edge:
                frm, to = edge.split(":", 1)
                parsed.add((frm, to))
            else:
                parsed.add(edge)
        return parsed

    @field_serializer("sea_edges", "coastal_edges", when_used="json")
    def _serialize_json_graph_edges(
        self,
        value: Set[Tuple[str, str]],
    ) -> list[str]:
        return [f"{frm}:{to}" for frm, to in sorted(value)]
