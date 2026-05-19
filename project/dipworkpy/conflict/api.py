from fastapi import APIRouter

from dipworkpy.conflict.model import ConflictRequest, ConflictResponse
from dipworkpy.conflict_game import conflict_game
from dipworkpy.model import Situation

router = APIRouter()


@router.post("/", response_model=ConflictResponse)
def post_conflict(req: ConflictRequest) -> ConflictResponse:
    sit = Situation(orders=req.orders, switches=req.switches)
    resolution = conflict_game(sit, order_geo_info=req.order_geo_info, convoy_graph=req.convoy_graph)
    return ConflictResponse(resolution=resolution)
