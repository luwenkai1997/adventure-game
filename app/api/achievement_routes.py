import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.container import container
from app.services import achievement_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/achievements")
async def get_achievements(request: Request):
    ctx = container.context_resolver.resolve_optional(request)
    if ctx is None:
        return JSONResponse(content={"achievements": [], "stats": {}})
    achievements = achievement_service.get_achievements_with_status(container.paths, ctx)
    state = achievement_service.load_state(container.paths, ctx)
    return JSONResponse(content={"achievements": achievements, "stats": state["stats"]})
