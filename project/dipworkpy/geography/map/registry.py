"""Map registry - look up maps by id, register custom ones."""

from __future__ import annotations

from typing import Dict, List

from dipworkpy.geography.map.protocol import MapProtocol
from dipworkpy.geography.map.standard import StandardMap

_registry: Dict[str, MapProtocol] = {}


def _bootstrap() -> None:
    if "standard" not in _registry:
        _registry["standard"] = StandardMap()


def get_map(map_id: str) -> MapProtocol:
    _bootstrap()
    if map_id not in _registry:
        raise KeyError(f"unknown map_id: {map_id!r}")
    return _registry[map_id]


def register_map(m: MapProtocol) -> None:
    _bootstrap()
    _registry[m.map_id] = m


def list_maps() -> List[str]:
    _bootstrap()
    return sorted(_registry.keys())
