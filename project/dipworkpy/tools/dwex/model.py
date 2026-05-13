"""DDL AST - the parsed shape of a .dwex file."""
from __future__ import annotations

from typing import Dict, List, Literal, Optional, Set

from pydantic import BaseModel, Field

PassableStr = Literal["ja", "nein", "-", "imp"]


class DwexField(BaseModel):
    name: str
    type: str
    x: float
    y: float
    sub_of: Optional[str] = None


class DwexEdge(BaseModel):
    a: str
    b: str
    army: str = "ja"
    fleet: str = "ja"
    convoy_move: str = "ja"
    directed: bool = False


class DwexUnit(BaseModel):
    nation: str
    utype: str
    current: str


class DwexOrderSpec(BaseModel):
    nation: str
    utype: str
    current: str
    order: str  # hld, mve, hsup, msup, con
    dest: Optional[str] = None
    expected_failed: bool = False
    expected_dislodged: bool = False


class DwexDocument(BaseModel):
    title: str
    description: str = ""
    fields: List[DwexField] = Field(default_factory=list)
    edges: List[DwexEdge] = Field(default_factory=list)
    units: List[DwexUnit] = Field(default_factory=list)
    orders: List[DwexOrderSpec] = Field(default_factory=list)
    switches: dict = Field(default_factory=dict)
    expected_pattfields: Set[str] = Field(default_factory=set)
    note: str = ""
    # Rendering pragmas read from a `pragmas { ... }` block. Key is the
    # kebab-case name; value is the argument string of `name(arg)` form, or
    # None for flag-style pragmas. `name in doc.pragmas` still works for
    # flag-style checks because Python's `in` on a dict tests keys.
    # Examples: 'no-mid-arrows' (flag), 'field-jitter(0.05)' (valued).
    pragmas: Dict[str, Optional[str]] = Field(default_factory=dict)
