import random

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.container import container
from app.models.check import CheckRequest, get_difficulty_color, get_difficulty_name


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


@router.get("/api/check/difficulty/{dc}")
async def get_difficulty_info(dc: int):
    return JSONResponse(
        content={
            "dc": dc,
            "name": get_difficulty_name(dc),
            "color": get_difficulty_color(dc),
        }
    )


@router.get("/api/check/roll")
async def roll_dice(dice: str = "d20"):
    _faces = {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12, "d20": 20, "d100": 100}
    faces = _faces.get(dice.lower(), 20)
    result = random.randint(1, faces)
    return JSONResponse(content={"dice": dice, "result": result})
