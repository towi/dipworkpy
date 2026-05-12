from fastapi import APIRouter

from dipworkpy.round.orchestrator import RoundRequest, RoundResult, round_full

router = APIRouter()


@router.post("/", response_model=RoundResult)
def post_round(req: RoundRequest) -> RoundResult:
    return round_full(req)
