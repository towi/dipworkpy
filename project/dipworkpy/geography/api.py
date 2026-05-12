"""Geography FastAPI router."""
from fastapi import APIRouter

from dipworkpy.geography.model import GeographyRequest, GeographyResponse
from dipworkpy.geography.service import geography_phase

router = APIRouter()


@router.post("/", response_model=GeographyResponse)
def post_geography(req: GeographyRequest) -> GeographyResponse:
    return geography_phase(req)
