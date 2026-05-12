from fastapi import APIRouter

from dipworkpy.syntax.model import SyntaxRequest, SyntaxResponse
from dipworkpy.syntax.service import syntax_phase

router = APIRouter()


@router.post("/", response_model=SyntaxResponse)
def post_syntax(req: SyntaxRequest) -> SyntaxResponse:
    return syntax_phase(req)
