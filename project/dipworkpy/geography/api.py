"""Geography FastAPI router."""

from fastapi import APIRouter

from dipworkpy.geography.model import (
    GeographyRequest,
    GeographyResponse,
    RetreatOptionsRequest,
    RetreatOptionsResponse,
)
from dipworkpy.geography.retreat import retreat_options
from dipworkpy.geography.service import geography_phase

router = APIRouter()


@router.post("/", response_model=GeographyResponse)
def post_geography(req: GeographyRequest) -> GeographyResponse:
    return geography_phase(req)


@router.post("/retreat-options", response_model=RetreatOptionsResponse)
def post_retreat_options(req: RetreatOptionsRequest) -> RetreatOptionsResponse:
    return retreat_options(req)
