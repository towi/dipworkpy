"""FastAPI app mounting every service router."""
from fastapi import FastAPI

from dipworkpy.conflict.api import router as conflict_router
from dipworkpy.geography.api import router as geography_router
from dipworkpy.round.api import router as round_router
from dipworkpy.syntax.api import router as syntax_router


def create_app() -> FastAPI:
    app = FastAPI(title="DipworkPy")
    app.include_router(syntax_router, prefix="/syntax", tags=["syntax"])
    app.include_router(geography_router, prefix="/geography", tags=["geography"])
    app.include_router(conflict_router, prefix="/conflict", tags=["conflict"])
    app.include_router(round_router, prefix="/round", tags=["round"])

    @app.get("/")
    def root() -> dict:
        return {"service": "dipworkpy", "endpoints": [
            "/syntax", "/geography", "/conflict", "/round",
        ]}

    return app


app = create_app()
