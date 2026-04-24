import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.container import container
from app.models.player import (
    ATTRIBUTE_NAMES_CN,
    ATTRIBUTE_NAMES_EN,
    PRESET_SKILLS,
    PlayerCreateRequest,
    PlayerRandomRequest,
    PlayerUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/player/skills")
async def get_preset_skills():
    return JSONResponse(
        content={"skills": PRESET_SKILLS, "attribute_names": ATTRIBUTE_NAMES_CN}
    )


@router.get("/api/player/attributes")
async def get_attribute_names():
    return JSONResponse(
        content={"en_to_cn": ATTRIBUTE_NAMES_CN, "cn_to_en": ATTRIBUTE_NAMES_EN}
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
    try:
        player = await asyncio.wait_for(
            container.player_service.generate_player_with_llm(ctx, world_setting),
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


@router.get("/api/player/summary")
async def get_player_summary(request: Request):
    ctx = container.context_resolver.resolve_optional(request)
    summary = container.player_service.get_player_summary(ctx)
    return JSONResponse(content={"summary": summary})


@router.post("/api/player/skill/{skill_name}")
async def add_skill(request: Request, skill_name: str):
    ctx = container.context_resolver.resolve_required(request)
    player = container.player_service.add_skill(ctx, skill_name)
    if not player:
        return JSONResponse(status_code=404, content={"error": "角色或技能不存在"})
    return JSONResponse(content={"success": True, "player": player.model_dump()})


@router.delete("/api/player/skill/{skill_name}")
async def remove_skill(request: Request, skill_name: str):
    ctx = container.context_resolver.resolve_required(request)
    player = container.player_service.remove_skill(ctx, skill_name)
    if not player:
        return JSONResponse(status_code=404, content={"error": "角色不存在"})
    return JSONResponse(content={"success": True, "player": player.model_dump()})


@router.post("/api/player/hp")
async def update_hp(request: Request, delta: int):
    ctx = container.context_resolver.resolve_required(request)
    player = container.player_service.update_hp(ctx, delta)
    if not player:
        return JSONResponse(status_code=404, content={"error": "角色不存在"})
    return JSONResponse(content={"success": True, "player": player.model_dump()})


@router.delete("/api/player")
async def delete_player(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    if container.player_repository.delete(ctx):
        return JSONResponse(content={"success": True})
    return JSONResponse(status_code=404, content={"error": "玩家角色不存在"})
