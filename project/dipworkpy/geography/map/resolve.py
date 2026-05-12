"""Resolve a MapRef into a concrete MapProtocol instance."""
from __future__ import annotations

from dipworkpy.geo_model import MapRef
from dipworkpy.geography.map.inline import InlineMap
from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.geography.map.registry import get_map


def resolve_map_ref(ref: MapRef) -> MapProtocol:
    """Inline wins; otherwise look up by map_id (default 'standard')."""
    if ref.inline_map is not None:
        return InlineMap(ref.inline_map)
    return get_map(ref.map_id or "standard")
