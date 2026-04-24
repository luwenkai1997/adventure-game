from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.container import container
from app.models.check import CheckRequest


router = APIRouter()


@router.post("/api/check")
async def perform_check(request: Request, body: CheckRequest):
    ctx = container.context_resolver.resolve_optional(request)
    result = container.check_service.perform_check(ctx, body)
    return JSONResponse(content={"success": True, "result": result.model_dump()})


@router.get("/api/check/info")
async def get_check_info(request: Request):
    ctx = container.context_resolver.resolve_optional(request)
    info = container.check_service.get_player_check_info(ctx)
    return JSONResponse(content={"success": True, "info": info})
