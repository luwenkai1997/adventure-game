import asyncio
import logging
import os

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import (
    API_BASE_URL,
    API_IMAGE_ENABLED,
    API_IMAGE_MODEL,
    API_KEY,
    NPC_DIALOGUE_PROMPT,
    RELATION_TYPES,
)
from app.container import container
from app.errors import AppError
from app.models.character import (
    CharacterCreate,
    CharacterUpdate,
    RelationCreate,
    RelationUpdate,
)
from app.models.chat import NPCDialogueRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/characters")
async def get_characters(request: Request):
    ctx = container.context_resolver.resolve_optional(request)
    characters = container.character_repository.load_all(ctx)
    return JSONResponse(content={"characters": characters})


@router.get("/api/characters/graph")
async def get_character_graph(request: Request):
    ctx = container.context_resolver.resolve_optional(request)
    graph_data = container.character_service.get_character_graph(ctx)
    return JSONResponse(content=graph_data)


@router.post("/api/characters/{char_id}/avatar")
async def generate_character_avatar(request: Request, char_id: str):
    """Generate and cache an avatar image for an NPC using the image generation API."""
    if not API_IMAGE_ENABLED:
        return JSONResponse(status_code=503, content={"error": "图像生成功能未启用，请在 .env 中设置 API_IMAGE_ENABLED=true"})

    ctx = container.context_resolver.resolve_required(request)
    character = container.character_repository.load(ctx, char_id)
    if not character:
        return JSONResponse(status_code=404, content={"error": "角色不存在"})

    # Build image prompt from appearance data
    appearance = character.get("appearance") or {}
    avatar_prompt = appearance.get("avatar_prompt") or appearance.get("full_description") or ""
    name = character.get("name", char_id)
    if not avatar_prompt:
        return JSONResponse(status_code=400, content={"error": "该角色缺少 avatar_prompt，无法生成头像"})

    prompt = f"Portrait of {name}. {avatar_prompt}. Detailed digital art, character portrait, high quality."

    # Call image generation API
    image_url_path = f"images/generations"
    base = API_BASE_URL.rstrip("/")
    # Navigate up from /v1 to root if needed
    endpoint = f"{base}/{image_url_path}"

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": API_IMAGE_MODEL, "prompt": prompt, "n": 1, "size": "512x512", "response_format": "url"}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(endpoint, headers=headers, json=payload)
        resp.raise_for_status()
        result = resp.json()

    image_url = result["data"][0]["url"]

    # Download and save the image locally
    async with httpx.AsyncClient(timeout=60) as client:
        img_resp = await client.get(image_url)
        img_resp.raise_for_status()
        img_bytes = img_resp.content

    char_dir = container.paths.character_dir(ctx)
    os.makedirs(char_dir, exist_ok=True)
    local_path = os.path.join(char_dir, f"{char_id}.png")
    with open(local_path, "wb") as f:
        f.write(img_bytes)

    # Persist the avatar URL on the character record
    game_id = ctx.game_id
    serve_url = f"/game-assets/{game_id}/character/{char_id}.png"
    character["avatar_url"] = serve_url
    container.character_repository.save(ctx, character)

    return JSONResponse(content={"avatar_url": serve_url})


@router.get("/api/characters/{char_id}")
async def get_character(request: Request, char_id: str):
    ctx = container.context_resolver.resolve_optional(request)
    character = container.character_repository.load(ctx, char_id)
    if not character:
        return JSONResponse(status_code=404, content={"error": "角色不存在"})
    return JSONResponse(content={"character": character})


@router.post("/api/characters")
async def create_character(request: Request, body: CharacterCreate):
    ctx = container.context_resolver.resolve_required(request)
    character = body.model_dump()
    char_id = container.character_repository.save(ctx, character)
    return JSONResponse(content={"success": True, "id": char_id, "character": character})


@router.put("/api/characters/{char_id}")
async def update_character(request: Request, char_id: str, body: CharacterUpdate):
    ctx = container.context_resolver.resolve_required(request)
    character = container.character_repository.load(ctx, char_id)
    if not character:
        return JSONResponse(status_code=404, content={"error": "角色不存在"})
    character.update(body.model_dump(exclude_none=True))
    container.character_repository.save(ctx, character)
    return JSONResponse(content={"success": True, "character": character})


@router.delete("/api/characters/{char_id}")
async def del_character(request: Request, char_id: str):
    ctx = container.context_resolver.resolve_required(request)
    if container.character_repository.delete(ctx, char_id):
        relations = container.relation_repository.load_all(ctx)
        relations = [
            relation
            for relation in relations
            if relation["source_id"] != char_id and relation["target_id"] != char_id
        ]
        container.relation_repository.save_all(ctx, relations)
        return JSONResponse(content={"success": True})
    return JSONResponse(status_code=404, content={"error": "角色不存在"})


@router.post("/api/npcs/generate")
async def api_generate_npcs(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    data = await request.json()
    world_setting = data.get("world_setting", "")
    protagonist_info = data.get("protagonist_info", {})
    npc_count = data.get("npc_count", 10)

    if not world_setting:
        return JSONResponse(status_code=400, content={"error": "缺少故事设定"})
    if not protagonist_info:
        return JSONResponse(status_code=400, content={"error": "缺少主角信息"})

    try:
        npcs = await asyncio.wait_for(
            container.character_service.generate_npcs_with_llm(
                ctx, world_setting, protagonist_info, npc_count
            ),
            timeout=120.0,
        )
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"error": "NPC生成超时，请稍后重试"})

    if not npcs:
        return JSONResponse(status_code=500, content={"error": "未能生成任何NPC"})

    saved_count = container.character_repository.save_batch(ctx, npcs)
    try:
        relations = await asyncio.wait_for(
            container.character_service.generate_relations(ctx, npcs, world_setting),
            timeout=120.0,
        )
        for relation in relations:
            container.relation_repository.add(ctx, relation)
    except asyncio.TimeoutError:
        relations = []
        logger.warning("关系生成超时，继续返回已生成的NPC")

    return JSONResponse(
        content={
            "success": True,
            "npcs_count": saved_count,
            "relations_count": len(relations),
            "npcs": npcs[:5],
            "message": f"成功生成 {saved_count} 个NPC和 {len(relations)} 个关系",
        }
    )


@router.get("/api/relations")
async def get_relations(request: Request):
    ctx = container.context_resolver.resolve_optional(request)
    relations = container.relation_repository.load_all(ctx)
    return JSONResponse(content={"relations": relations})


@router.post("/api/relations")
async def create_relation(request: Request, body: RelationCreate):
    ctx = container.context_resolver.resolve_required(request)
    source = container.character_repository.load(ctx, body.source_id)
    target = container.character_repository.load(ctx, body.target_id)
    if not source or not target:
        return JSONResponse(status_code=404, content={"error": "源角色或目标角色不存在"})

    relation = container.relation_repository.add(ctx, body.model_dump())
    return JSONResponse(content={"success": True, "relation": relation})


@router.put("/api/relations/{rel_id}")
async def update_rel(request: Request, rel_id: str, body: RelationUpdate):
    ctx = container.context_resolver.resolve_required(request)
    relation = container.relation_repository.update(
        ctx, rel_id, body.model_dump(exclude_none=True)
    )
    if not relation:
        return JSONResponse(status_code=404, content={"error": "关系不存在"})
    return JSONResponse(content={"success": True, "relation": relation})


@router.delete("/api/relations/{rel_id}")
async def del_relation(request: Request, rel_id: str):
    ctx = container.context_resolver.resolve_required(request)
    if container.relation_repository.delete(ctx, rel_id):
        return JSONResponse(content={"success": True})
    return JSONResponse(status_code=404, content={"error": "关系不存在"})


@router.get("/api/relation-types")
async def get_relation_types():
    return JSONResponse(content={"types": RELATION_TYPES})


@router.post("/api/characters/{char_id}/dialogue")
async def npc_dialogue(request: Request, char_id: str, body: NPCDialogueRequest):
    ctx = container.context_resolver.resolve_required(request)
    npc = container.character_repository.load(ctx, char_id)
    if not npc:
        return JSONResponse(status_code=404, content={"error": "NPC不存在"})

    player = container.player_repository.load(ctx)
    relations = container.relation_repository.load_all(ctx)
    npc_relations = [
        relation
        for relation in relations
        if relation.get("source_id") == char_id or relation.get("target_id") == char_id
    ]

    prompt = NPC_DIALOGUE_PROMPT.format(
        npc_name=npc.get("name", "未知NPC"),
        npc_title=npc.get("title", ""),
        npc_personality=npc.get("personality", {}).get("traits", [])
        if isinstance(npc.get("personality"), dict)
        else npc.get("personality", "神秘"),
        npc_background=npc.get("background", {}).get("backstory", "背景未知")
        if isinstance(npc.get("background"), dict)
        else npc.get("background", "背景未知"),
        npc_relation=_get_relation_description(npc, npc_relations, player),
        relation_events=_get_relation_events_description(npc_relations),
        context=body.context or "",
        player_message=body.message,
    )

    try:
        data = await container.llm_adapter.generate_json(
            ctx=ctx,
            prompt=prompt,
            method_name="npc_dialogue",
            use_utility_model=True,
        )
    except Exception:
        raw_response = await container.llm_adapter.generate_text(
            ctx=ctx,
            prompt=prompt,
            method_name="npc_dialogue_fallback",
            use_utility_model=True,
        )
        data = {"dialogue": raw_response, "mood": "平静", "relationship_hint": ""}

    return JSONResponse(
        content={
            "success": True,
            "dialogue": data.get("dialogue", ""),
            "mood": data.get("mood", "平静"),
            "relationship_hint": data.get("relationship_hint", ""),
        }
    )


def _get_relation_description(npc: dict, npc_relations: list, player: dict) -> str:
    if not npc_relations:
        return "陌生人"

    _ = player.get("name", "玩家") if player else "玩家"
    for relation in npc_relations:
        if relation.get("source_id") == npc.get("id"):
            target_name = relation.get("target_name", "")
            rel_type = relation.get("relation_type", "acquaintance")
            strength = relation.get("strength", 50)
            return f"与{target_name}的关系: {rel_type}（强度{strength}）"
        if relation.get("target_id") == npc.get("id"):
            source_name = relation.get("source_name", "")
            rel_type = relation.get("relation_type", "acquaintance")
            strength = relation.get("strength", 50)
            return f"被{source_name}视为{rel_type}（强度{strength}）"

    return "陌生人"


def _get_relation_events_description(npc_relations: list) -> str:
    if not npc_relations:
        return "无互动记录。"

    events = []
    for relation in npc_relations:
        events.extend(relation.get("events", []))

    if not events:
        return "无互动记录。"

    events = sorted(events, key=lambda x: x.get("timestamp", ""), reverse=False)[-10:]

    lines = []
    for event in events:
        change = f"{event.get('type', '')}{event.get('value', 0)}"
        reason = event.get('reason', '未知')
        lines.append(f"- 发生了【{reason}】，关系变化：{change}")

    return "\n".join(lines)
