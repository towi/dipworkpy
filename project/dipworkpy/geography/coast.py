"""Subfield (coast) resolution and superfield normalization.

GEO-007: when a fleet sits on a split-coast superfield (e.g. Spa) and the
move destination is reachable only from one coast, we resolve which.
GEO-008: outputs are always normalized to the superfield code; the
resolved coast travels in OrderGeoInfo.resolved_coast.
"""
from __future__ import annotations

from typing import Optional

from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.model import Order


def normalize_to_superfield(fld: str, m: MapProtocol) -> str:
    """SpN -> Spa, Vie -> Vie, Spa -> Spa."""
    if not m.field_exists(fld):
        return fld
    return m.superfield_of(fld)


def resolve_coast(o: Order, m: MapProtocol) -> Optional[str]:
    """If Fleet on a split-coast superfield, decide which coast based on dest."""
    if o.utype != "F" or o.dest is None:
        return None
    subs = m.subfields_of(o.current)
    if not subs:
        return None
    candidates = []
    for sub in subs:
        nbrs = m.neighbors(sub)
        if o.dest in nbrs:
            candidates.append(sub)
    if len(candidates) == 1:
        return candidates[0]
    return None
