import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.models.character import (
    CharacterCreate,
    CharacterUpdate,
    RelationCreate,
    RelationUpdate,
    GenerateCharactersRequest,
    CharacterGenerationConfig,
    BatchUpdateRequest,
)
from app.models.chat import NPCDialogueRequest
from app.services.character_service import CharacterService
from app.utils.file_storage import (
    load_characters,
    load_character,
    delete_character,
    save_character,
    save_characters_batch,
    load_relations,
    add_relation,
    update_relation,
    delete_relation,
    save_relations,
    load_player,
    load_memory,
)
from app.config import RELATION_TYPES, NPC_DIALOGUE_PROMPT
from app.utils.file_storage import get_snapshot_path
from app.services.llm_gateway import call_llm
from app.errors import AppError


router = APIRouter()
character_service = CharacterService()


@router.get("/api/characters")
async def get_characters():
    try:
        characters = load_characters()
        return JSONResponse(content={'characters': characters})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取角色列表失败: {str(e)}'})


@router.get("/api/characters/graph")
async def get_character_graph():
    try:
        graph_data = character_service.get_character_graph()
        return JSONResponse(content=graph_data)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取关系图数据失败: {str(e)}'})


@router.get("/api/characters/protagonist")
async def get_protagonist():
    try:
        characters = load_characters()
        protagonists = [c for c in characters if c.get('role_type') == 'protagonist']
        return JSONResponse(content={'characters': protagonists})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取主角失败: {str(e)}'})


@router.get("/api/characters/antagonists")
async def get_antagonists():
    try:
        characters = load_characters()
        antagonists = [c for c in characters if c.get('role_type') == 'antagonist']
        return JSONResponse(content={'characters': antagonists})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取反派失败: {str(e)}'})


@router.get("/api/characters/inject-context")
async def inject_character_context(character_ids: str = ""):
    try:
        ids = [id.strip() for id in character_ids.split(",") if id.strip()]
        context = character_service.get_character_context(ids)
        return JSONResponse(content={'context': context})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'注入上下文失败: {str(e)}'})


@router.get("/api/characters/by-role/{role_type}")
async def get_characters_by_role(role_type: str):
    try:
        characters = load_characters()
        filtered = [c for c in characters if c.get('role_type', 'npc') == role_type]
        return JSONResponse(content={'characters': filtered, 'count': len(filtered)})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取角色失败: {str(e)}'})


@router.get("/api/characters/snapshot/{chapter}")
async def get_character_snapshot(chapter: int):
    try:
        snapshot_path = get_snapshot_path(chapter)
        if os.path.exists(snapshot_path):
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
            return JSONResponse(content={'snapshot': snapshot})
        return JSONResponse(status_code=404, content={'error': '快照不存在'})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取快照失败: {str(e)}'})


@router.get("/api/characters/{char_id}")
async def get_character(char_id: str):
    try:
        character = load_character(char_id)
        if not character:
            return JSONResponse(status_code=404, content={'error': '角色不存在'})
        return JSONResponse(content={'character': character})
    except AppError:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取角色失败: {str(e)}'})


@router.post("/api/characters")
async def create_character(request: CharacterCreate):
    try:
        character = request.dict()
        char_id = save_character(character)
        return JSONResponse(content={'success': True, 'id': char_id, 'character': character})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'创建角色失败: {str(e)}'})


@router.put("/api/characters/{char_id}")
async def update_character(char_id: str, request: CharacterUpdate):
    try:
        character = load_character(char_id)
        if not character:
            return JSONResponse(status_code=404, content={'error': '角色不存在'})

        updates = request.dict(exclude_none=True)
        character.update(updates)
        save_character(character)

        return JSONResponse(content={'success': True, 'character': character})
    except AppError:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'更新角色失败: {str(e)}'})


@router.delete("/api/characters/{char_id}")
async def del_character(char_id: str):
    try:
        if delete_character(char_id):
            relations = load_relations()
            relations = [r for r in relations if r['source_id'] != char_id and r['target_id'] != char_id]
            save_relations(relations)
            return JSONResponse(content={'success': True})
        return JSONResponse(status_code=404, content={'error': '角色不存在'})
    except AppError:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'删除角色失败: {str(e)}'})


@router.post("/api/characters/generate")
async def api_generate_characters(request: GenerateCharactersRequest):
    import asyncio
    
    try:
        config = request.config or CharacterGenerationConfig(
            world_setting=request.world_setting
        )

        try:
            all_characters = await asyncio.wait_for(
                character_service.generate_all_characters(config),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504, 
                content={'error': '角色生成超时，请稍后重试'}
            )
        
        if not all_characters:
            return JSONResponse(
                status_code=500, 
                content={'error': '未能生成任何角色'}
            )
        
        # 保存角色
        saved_count = save_characters_batch(all_characters)
        
        # 生成关系（也设置超时）
        try:
            relations = await asyncio.wait_for(
                character_service.generate_relations(all_characters, config.world_setting),
                timeout=120.0,
            )
            for rel in relations:
                add_relation(rel)
        except asyncio.TimeoutError:
            relations = []
            print("关系生成超时，继续返回已生成的角色")

        return JSONResponse(content={
            'success': True,
            'characters_count': saved_count,
            'relations_count': len(relations),
            'characters': all_characters[:5],
            'message': f'成功生成 {saved_count} 个角色和 {len(relations)} 个关系'
        })
    except Exception as e:
        import traceback
        print(f"生成角色时出错: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={'error': f'生成角色失败: {str(e)}'})


@router.post("/api/npcs/generate")
async def api_generate_npcs(request: Request):
    """生成NPC - 在主角确认后调用"""
    import asyncio
    
    try:
        data = await request.json()
        world_setting = data.get('world_setting', '')
        protagonist_info = data.get('protagonist_info', {})
        npc_count = data.get('npc_count', 10)
        
        if not world_setting:
            return JSONResponse(status_code=400, content={'error': '缺少故事设定'})
        
        if not protagonist_info:
            return JSONResponse(status_code=400, content={'error': '缺少主角信息'})
        
        try:
            npcs = await asyncio.wait_for(
                character_service.generate_npcs_with_llm(
                    world_setting, protagonist_info, npc_count
                ),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={'error': 'NPC生成超时，请稍后重试'}
            )
        
        if not npcs:
            return JSONResponse(
                status_code=500,
                content={'error': '未能生成任何NPC'}
            )
        
        saved_count = save_characters_batch(npcs)
        
        try:
            relations = await asyncio.wait_for(
                character_service.generate_relations(npcs, world_setting),
                timeout=120.0,
            )
            for rel in relations:
                add_relation(rel)
        except asyncio.TimeoutError:
            relations = []
            print("关系生成超时，继续返回已生成的NPC")
        
        return JSONResponse(content={
            'success': True,
            'npcs_count': saved_count,
            'relations_count': len(relations),
            'npcs': npcs[:5],
            'message': f'成功生成 {saved_count} 个NPC和 {len(relations)} 个关系'
        })
    except Exception as e:
        import traceback
        print(f"生成NPC时出错: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={'error': f'生成NPC失败: {str(e)}'})


@router.post("/api/characters/batch-update")
async def api_batch_update_characters(request: BatchUpdateRequest):
    try:
        updated_count = character_service.batch_update(request.updates)
        return JSONResponse(content={'success': True, 'updated_count': updated_count})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'批量更新失败: {str(e)}'})


@router.post("/api/characters/snapshot/{chapter}")
async def create_character_snapshot(chapter: int):
    try:
        snapshot_path = character_service.create_snapshot(chapter)
        return JSONResponse(content={'success': True, 'snapshot_path': snapshot_path})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'创建快照失败: {str(e)}'})


@router.get("/api/relations")
async def get_relations():
    try:
        relations = load_relations()
        return JSONResponse(content={'relations': relations})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取关系列表失败: {str(e)}'})


@router.post("/api/relations")
async def create_relation(request: RelationCreate):
    try:
        source = load_character(request.source_id)
        target = load_character(request.target_id)
        if not source or not target:
            return JSONResponse(status_code=404, content={'error': '源角色或目标角色不存在'})

        relation = request.dict()
        new_rel = add_relation(relation)
        return JSONResponse(content={'success': True, 'relation': new_rel})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'创建关系失败: {str(e)}'})


@router.put("/api/relations/{rel_id}")
async def update_rel(rel_id: str, request: RelationUpdate):
    try:
        relation = update_relation(rel_id, request.dict(exclude_none=True))
        if not relation:
            return JSONResponse(status_code=404, content={'error': '关系不存在'})
        return JSONResponse(content={'success': True, 'relation': relation})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'更新关系失败: {str(e)}'})


@router.delete("/api/relations/{rel_id}")
async def del_relation(rel_id: str):
    try:
        if delete_relation(rel_id):
            return JSONResponse(content={'success': True})
        return JSONResponse(status_code=404, content={'error': '关系不存在'})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'删除关系失败: {str(e)}'})


@router.get("/api/relation-types")
async def get_relation_types():
    return JSONResponse(content={'types': RELATION_TYPES})


@router.post("/api/characters/{char_id}/dialogue")
async def npc_dialogue(char_id: str, request: NPCDialogueRequest):
    try:
        npc = load_character(char_id)
        if not npc:
            return JSONResponse(status_code=404, content={'error': 'NPC不存在'})
        
        player = load_player()
        memory = load_memory()
        relations = load_relations()
        
        npc_relations = [r for r in relations if r.get('source_id') == char_id or r.get('target_id') == char_id]
        
        prompt = NPC_DIALOGUE_PROMPT.format(
            npc_name=npc.get('name', '未知NPC'),
            npc_title=npc.get('title', ''),
            npc_personality=npc.get('personality', {}).get('traits', []) if isinstance(npc.get('personality'), dict) else npc.get('personality', '神秘'),
            npc_background=npc.get('background', {}).get('backstory', '背景未知') if isinstance(npc.get('background'), dict) else npc.get('background', '背景未知'),
            npc_relation=_get_relation_description(npc, npc_relations, player),
            context=request.context or '',
            player_message=request.message
        )
        
        response = await call_llm(prompt, method_name="npc_dialogue")
        
        import json as json_lib
        try:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                json_str = response[start:end+1]
                data = json_lib.loads(json_str)
            else:
                data = json_lib.loads(response)
        except:
            data = {"dialogue": response, "mood": "平静", "relationship_hint": ""}
        
        return JSONResponse(content={
            'success': True,
            'dialogue': data.get('dialogue', response),
            'mood': data.get('mood', '平静'),
            'relationship_hint': data.get('relationship_hint', '')
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'error': f'NPC对话失败: {str(e)}'})


def _get_relation_description(npc: dict, npc_relations: list, player: dict) -> str:
    if not npc_relations:
        return "陌生人"
    
    player_name = player.get('name', '玩家') if player else '玩家'
    
    for rel in npc_relations:
        if rel.get('source_id') == npc.get('id'):
            target_name = rel.get('target_name', '')
            rel_type = rel.get('relation_type', 'acquaintance')
            strength = rel.get('strength', 50)
            return f"与{target_name}的关系: {rel_type}（强度{strength}）"
        elif rel.get('target_id') == npc.get('id'):
            source_name = rel.get('source_name', '')
            rel_type = rel.get('relation_type', 'acquaintance')
            strength = rel.get('strength', 50)
            return f"被{source_name}视为{rel_type}（强度{strength}）"
    
    return "陌生人"
