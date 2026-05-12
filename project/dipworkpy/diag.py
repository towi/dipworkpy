"""Diagnostic - structured audit-trail entry produced by every service."""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class Diagnostic(BaseModel):
    """One structured entry in a phase's audit trail.

    Every rule evaluation emits one Diagnostic - even no-ops with
    severity='info' - so a consuming UI can show *which* rules were checked,
    not just which fired.
    """
    phase: Literal["syntax", "geography", "conflict", "round"]
    rule: str
    severity: Literal["info", "warning", "correction", "error"]
    order_index: Optional[int] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
