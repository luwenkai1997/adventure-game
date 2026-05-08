import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.container import container
from app.models.player import (
    ATTRIBUTE_NAMES_CN,
    PlayerCreateRequest,
    PlayerRandomRequest,
    PlayerUpdateRequest,
    get_preset_skills_for_scenario,
)
from app.scenarios import DEFAULT_SCENARIO_TYPE, normalize_scenario_type

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/player/skills")
async def get_preset_skills(scenario_type: str = DEFAULT_SCENARIO_TYPE):
    normalized = normalize_scenario_type(scenario_type)
    return JSONResponse(
        content={
            "skills": get_preset_skills_for_scenario(normalized),
            "attribute_names": ATTRIBUTE_NAMES_CN,
            "scenario_type": normalized,
        }
    )


@router.post("/api/player/create")
async def create_player(request: Request, body: PlayerCreateRequest):
    ctx = container.context_resolver.resolve_required(request)
    player = container.player_service.create_player(ctx, body)
    return JSONResponse(content={"success": True, "player": player.model_dump()})


@router.post("/api/player/random")
async def random_player(request: Request, body: Optional[PlayerRandomRequest] = None):
    ctx = container.context_resolver.resolve_required(request)
    player = container.player_service.random_player(ctx, body)
    return JSONResponse(content={"success": True, "player": player.model_dump()})


@router.post("/api/player/generate")
async def generate_player(request: Request, body: Optional[PlayerRandomRequest] = None):
    ctx = container.context_resolver.resolve_required(request)
    world_setting = body.world_setting if body else ""
    scenario_type = normalize_scenario_type(body.scenario_type if body else None)
    try:
        player = await asyncio.wait_for(
            container.player_service.generate_player_with_llm(
                ctx, world_setting, scenario_type=scenario_type
            ),
            timeout=120.0,
        )
        if player:
            return JSONResponse(content={"success": True, "player": player.model_dump()})

        player = container.player_service.random_player(ctx, body)
        return JSONResponse(
            content={
                "success": True,
                "player": player.model_dump(),
                "warning": "LLM生成失败，已使用随机角色",
            }
        )
    except asyncio.TimeoutError:
        player = container.player_service.random_player(ctx, body)
        return JSONResponse(
            content={
                "success": True,
                "player": player.model_dump(),
                "warning": "LLM生成超时，已使用随机角色",
            }
        )


@router.get("/api/player")
async def get_player(request: Request):
    ctx = container.context_resolver.resolve_optional(request)
    player = container.player_service.get_player(ctx)
    if not player:
        return JSONResponse(content={"exists": False, "player": None})
    return JSONResponse(content={"exists": True, "player": player.model_dump()})


@router.put("/api/player")
async def update_player(request: Request, body: PlayerUpdateRequest):
    ctx = container.context_resolver.resolve_required(request)
    updates = body.model_dump(exclude_none=True)
    player = container.player_service.update_player(ctx, updates)
    if not player:
        return JSONResponse(status_code=404, content={"error": "玩家角色不存在"})
    return JSONResponse(content={"success": True, "player": player.model_dump()})
