import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import NPC_DIALOGUE_PROMPT, RELATION_TYPES
from app.container import container
from app.errors import AppError
from app.models.character import (
    BatchUpdateRequest,
    CharacterCreate,
    CharacterGenerationConfig,
    CharacterUpdate,
    GenerateCharactersRequest,
    RelationCreate,
    RelationUpdate,
)
from app.models.chat import NPCDialogueRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/characters")
async def get_characters(request: Request):
    try:
        ctx = container.context_resolver.resolve_optional(request)
        characters = container.character_repository.load_all(ctx)
        return JSONResponse(content={"characters": characters})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取角色列表失败: {str(e)}"})


@router.get("/api/characters/graph")
async def get_character_graph(request: Request):
    try:
        ctx = container.context_resolver.resolve_optional(request)
        graph_data = container.character_service.get_character_graph(ctx)
        return JSONResponse(content=graph_data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取关系图数据失败: {str(e)}"})


@router.get("/api/characters/protagonist")
async def get_protagonist(request: Request):
    try:
        ctx = container.context_resolver.resolve_optional(request)
        characters = container.character_repository.load_all(ctx)
        protagonists = [char for char in characters if char.get("role_type") == "protagonist"]
        return JSONResponse(content={"characters": protagonists})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取主角失败: {str(e)}"})


@router.get("/api/characters/antagonists")
async def get_antagonists(request: Request):
    try:
        ctx = container.context_resolver.resolve_optional(request)
        characters = container.character_repository.load_all(ctx)
        antagonists = [char for char in characters if char.get("role_type") == "antagonist"]
        return JSONResponse(content={"characters": antagonists})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取反派失败: {str(e)}"})


@router.get("/api/characters/inject-context")
async def inject_character_context(request: Request, character_ids: str = ""):
    try:
        ctx = container.context_resolver.resolve_optional(request)
        ids = [item.strip() for item in character_ids.split(",") if item.strip()]
        context = container.character_service.get_character_context(ctx, ids)
        return JSONResponse(content={"context": context})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"注入上下文失败: {str(e)}"})


@router.get("/api/characters/by-role/{role_type}")
async def get_characters_by_role(request: Request, role_type: str):
    try:
        ctx = container.context_resolver.resolve_optional(request)
        characters = container.character_repository.load_all(ctx)
        filtered = [char for char in characters if char.get("role_type", "npc") == role_type]
        return JSONResponse(content={"characters": filtered, "count": len(filtered)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取角色失败: {str(e)}"})


@router.get("/api/characters/snapshot/{chapter}")
async def get_character_snapshot(request: Request, chapter: int):
    try:
        ctx = container.context_resolver.resolve_required(request)
        snapshot = container.snapshot_repository.load(ctx, chapter)
        if snapshot is None:
            return JSONResponse(status_code=404, content={"error": "快照不存在"})
        return JSONResponse(content={"snapshot": snapshot})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取快照失败: {str(e)}"})


@router.get("/api/characters/{char_id}")
async def get_character(request: Request, char_id: str):
    try:
        ctx = container.context_resolver.resolve_optional(request)
        character = container.character_repository.load(ctx, char_id)
        if not character:
            return JSONResponse(status_code=404, content={"error": "角色不存在"})
        return JSONResponse(content={"character": character})
    except AppError:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取角色失败: {str(e)}"})


@router.post("/api/characters")
async def create_character(request: Request, body: CharacterCreate):
    try:
        ctx = container.context_resolver.resolve_required(request)
        character = body.model_dump()
        char_id = container.character_repository.save(ctx, character)
        return JSONResponse(content={"success": True, "id": char_id, "character": character})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"创建角色失败: {str(e)}"})


@router.put("/api/characters/{char_id}")
async def update_character(request: Request, char_id: str, body: CharacterUpdate):
    try:
        ctx = container.context_resolver.resolve_required(request)
        character = container.character_repository.load(ctx, char_id)
        if not character:
            return JSONResponse(status_code=404, content={"error": "角色不存在"})
        character.update(body.model_dump(exclude_none=True))
        container.character_repository.save(ctx, character)
        return JSONResponse(content={"success": True, "character": character})
    except AppError:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"更新角色失败: {str(e)}"})


@router.delete("/api/characters/{char_id}")
async def del_character(request: Request, char_id: str):
    try:
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
    except AppError:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"删除角色失败: {str(e)}"})


@router.post("/api/characters/generate")
async def api_generate_characters(request: Request, body: GenerateCharactersRequest):
    import asyncio

    try:
        ctx = container.context_resolver.resolve_required(request)
        config = body.config or CharacterGenerationConfig(world_setting=body.world_setting)
        try:
            all_characters = await asyncio.wait_for(
                container.character_service.generate_all_characters(ctx, config),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            return JSONResponse(status_code=504, content={"error": "角色生成超时，请稍后重试"})

        if not all_characters:
            return JSONResponse(status_code=500, content={"error": "未能生成任何角色"})

        saved_count = container.character_repository.save_batch(ctx, all_characters)
        try:
            relations = await asyncio.wait_for(
                container.character_service.generate_relations(
                    ctx, all_characters, config.world_setting
                ),
                timeout=120.0,
            )
            for relation in relations:
                container.relation_repository.add(ctx, relation)
        except asyncio.TimeoutError:
            relations = []
            logger.warning("关系生成超时，继续返回已生成的角色")

        return JSONResponse(
            content={
                "success": True,
                "characters_count": saved_count,
                "relations_count": len(relations),
                "characters": all_characters[:5],
                "message": f"成功生成 {saved_count} 个角色和 {len(relations)} 个关系",
            }
        )
    except Exception as e:
        logger.error("生成角色时出错: %s", str(e), exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"生成角色失败: {str(e)}"})


@router.post("/api/npcs/generate")
async def api_generate_npcs(request: Request):
    import asyncio

    try:
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
    except Exception as e:
        logger.error("生成NPC时出错: %s", str(e), exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"生成NPC失败: {str(e)}"})


@router.post("/api/characters/batch-update")
async def api_batch_update_characters(request: Request, body: BatchUpdateRequest):
    try:
        ctx = container.context_resolver.resolve_required(request)
        updated_count = container.character_service.batch_update(ctx, body.updates)
        return JSONResponse(content={"success": True, "updated_count": updated_count})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"批量更新失败: {str(e)}"})


@router.post("/api/characters/snapshot/{chapter}")
async def create_character_snapshot(request: Request, chapter: int):
    try:
        ctx = container.context_resolver.resolve_required(request)
        snapshot_path = container.character_service.create_snapshot(ctx, chapter)
        return JSONResponse(content={"success": True, "snapshot_path": snapshot_path})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"创建快照失败: {str(e)}"})


@router.get("/api/relations")
async def get_relations(request: Request):
    try:
        ctx = container.context_resolver.resolve_optional(request)
        relations = container.relation_repository.load_all(ctx)
        return JSONResponse(content={"relations": relations})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取关系列表失败: {str(e)}"})


@router.post("/api/relations")
async def create_relation(request: Request, body: RelationCreate):
    try:
        ctx = container.context_resolver.resolve_required(request)
        source = container.character_repository.load(ctx, body.source_id)
        target = container.character_repository.load(ctx, body.target_id)
        if not source or not target:
            return JSONResponse(status_code=404, content={"error": "源角色或目标角色不存在"})

        relation = container.relation_repository.add(ctx, body.model_dump())
        return JSONResponse(content={"success": True, "relation": relation})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"创建关系失败: {str(e)}"})


@router.put("/api/relations/{rel_id}")
async def update_rel(request: Request, rel_id: str, body: RelationUpdate):
    try:
        ctx = container.context_resolver.resolve_required(request)
        relation = container.relation_repository.update(
            ctx, rel_id, body.model_dump(exclude_none=True)
        )
        if not relation:
            return JSONResponse(status_code=404, content={"error": "关系不存在"})
        return JSONResponse(content={"success": True, "relation": relation})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"更新关系失败: {str(e)}"})


@router.delete("/api/relations/{rel_id}")
async def del_relation(request: Request, rel_id: str):
    try:
        ctx = container.context_resolver.resolve_required(request)
        if container.relation_repository.delete(ctx, rel_id):
            return JSONResponse(content={"success": True})
        return JSONResponse(status_code=404, content={"error": "关系不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"删除关系失败: {str(e)}"})


@router.get("/api/relation-types")
async def get_relation_types():
    return JSONResponse(content={"types": RELATION_TYPES})


@router.post("/api/characters/{char_id}/dialogue")
async def npc_dialogue(request: Request, char_id: str, body: NPCDialogueRequest):
    try:
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
            )
        except Exception:
            raw_response = await container.llm_adapter.generate_text(
                ctx=ctx,
                prompt=prompt,
                method_name="npc_dialogue_fallback",
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
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"NPC对话失败: {str(e)}"})


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
