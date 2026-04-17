import os
import json
import uuid
import logging
from typing import Optional, List, Dict
from datetime import datetime
import asyncio
from app.config import (
    CHARACTER_LIST_GENERATION_PROMPT,
    CHARACTER_DETAIL_GENERATION_PROMPT,
    RELATION_GENERATION_PROMPT,
    ROLE_DESCRIPTIONS,
    ROLE_TYPE_CN,
    ROLE_IMPORTANCE,
    RELATION_TYPES,
)
from app.models.character import (
    AttributesModel,
    AppearanceModel,
    BackgroundModel,
    PersonalityModel,
    StatusModel,
    CharacterGenerationConfig,
)
from app.game_context import GameContext


logger = logging.getLogger(__name__)


class CharacterService:
    def __init__(
        self,
        character_repository,
        relation_repository,
        snapshot_repository,
        llm_adapter,
    ):
        self.character_repository = character_repository
        self.relation_repository = relation_repository
        self.snapshot_repository = snapshot_repository
        self.llm_adapter = llm_adapter

    def _try_fix_truncated_json(self, content: str) -> List[dict]:
        import re
        import json
        
        if not content:
            return []
        
        try:
            complete_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
            npcs = []
            for obj_str in complete_objects:
                try:
                    npc = json.loads(obj_str)
                    if isinstance(npc, dict) and 'name' in npc:
                        npcs.append(npc)
                except:
                    continue
            if npcs:
                logger.info("成功从截断的JSON中提取了 %s 个NPC", len(npcs))
                return npcs
        except Exception as e:
            logger.warning("修复截断JSON失败: %s", str(e)[:100])
        
        return []

    async def generate_npcs_with_llm(
        self,
        ctx: Optional[GameContext],
        world_setting: str, 
        protagonist_info: dict,
        count: int = 10
    ) -> List[dict]:
        from app.config import NPC_LIST_GENERATION_PROMPT, NPC_DETAIL_GENERATION_PROMPT

        protagonist_summary = f"""
姓名: {protagonist_info.get('name', '未知')}
种族: {protagonist_info.get('race', '未知')}
称号: {protagonist_info.get('title', '无')}
背景: {protagonist_info.get('background', '未知')}
性格: {protagonist_info.get('personality', '未知')}
""".strip()
        
        list_prompt = NPC_LIST_GENERATION_PROMPT.format(
            count=count,
            world_setting=world_setting,
            protagonist_info=protagonist_summary
        )
        
        system_prompt_list = "你是一个专业的角色设计师，擅长角色设计。请严格按照JSON数组格式返回简练的名录。"
        
        response_list = await self.llm_adapter.generate_json(
            ctx=ctx,
            prompt=list_prompt,
            system_prompt=system_prompt_list,
            timeout=120,
            method_name="generate_npc_list",
        )
        
        try:
            npcs_list = response_list
        except Exception as e:
            logger.warning("NPC名录 JSON解析失败，尝试修复: %s", str(e)[:200])
            npcs_list = self._try_fix_truncated_json(str(response_list))
        
        if not npcs_list or not isinstance(npcs_list, list):
            logger.warning("LLM返回格式错误，无法解析NPC名录数据")
            return []
            
        npcs_list = npcs_list[:count]
        
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_npc_detail(npc_basic):
            async with semaphore:
                detail_prompt = NPC_DETAIL_GENERATION_PROMPT.format(
                    world_setting=world_setting,
                    protagonist_info=protagonist_summary,
                    npc_name=npc_basic.get('name', '未知'),
                    npc_title=npc_basic.get('title', ''),
                    role_type=npc_basic.get('role_type', 'npc'),
                    relation_to_protagonist=npc_basic.get('relation_to_protagonist', ''),
                    story_role=npc_basic.get('story_role', '')
                )
                system_prompt_detail = "你是一个专业的角色设计师。请严格按照JSON格式返回角色详细设定。"
                try:
                    detail_data = await self.llm_adapter.generate_json(
                        ctx=ctx,
                        prompt=detail_prompt,
                        system_prompt=system_prompt_detail,
                        timeout=180,
                        method_name="generate_npc_detail",
                    )
                    if isinstance(detail_data, dict):
                        return detail_data
                except Exception as e:
                    logger.warning("生成NPC %s 详细信息失败: %s", npc_basic.get('name'), e)
                return None

        logger.info("开始并发生成 %s 个NPC详细信息...", len(npcs_list))
        details_results = await asyncio.gather(*(fetch_npc_detail(npc) for npc in npcs_list))
        
        npcs = []
        for detail_data in details_results:
            if not detail_data:
                continue
            
            attributes = detail_data.get('attributes', {})
            
            npc = {
                'id': f"char_{uuid.uuid4().hex[:8]}",
                'name': detail_data.get('name', '未知NPC'),
                'age': detail_data.get('age', 25),
                'gender': detail_data.get('gender', '其他'),
                'race': detail_data.get('race', '人类'),
                'role_type': detail_data.get('role_type', 'npc'),
                'importance': 3 if detail_data.get('role_type') == 'antagonist' else (2 if detail_data.get('role_type') == 'supporting' else 1),
                'title': detail_data.get('title', ''),
                'description': detail_data.get('background', detail_data.get('appearance', '')),
                'appearance': {
                    'full_description': detail_data.get('appearance', '外貌普通')
                },
                'background': {
                    'backstory': detail_data.get('background', ''),
                    'occupation': detail_data.get('title', '')
                },
                'personality': {
                    'traits': detail_data.get('personality', '').split('、') if detail_data.get('personality') else []
                },
                'attributes': {
                    'health': 100,
                    'mana': 100,
                    'strength': attributes.get('strength', 10) if isinstance(attributes, dict) else 10,
                    'agility': attributes.get('agility', 10) if isinstance(attributes, dict) else 10,
                    'intelligence': attributes.get('intelligence', 10) if isinstance(attributes, dict) else 10,
                    'charisma': attributes.get('charisma', 10) if isinstance(attributes, dict) else 10,
                    'luck': 10
                },
                'status': {
                    'current_state': 'active',
                    'mood': 'neutral',
                    'conditions': []
                },
                'skills': detail_data.get('skills', []),
                'tags': [],
                'relation_to_protagonist': detail_data.get('relation_to_protagonist', ''),
                'story_role': detail_data.get('story_role', ''),
                'plot_connection': detail_data.get('plot_connection', ''),
                'generated_by': 'auto',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            npcs.append(npc)
        
        logger.info("成功生成 %s 个NPC", len(npcs))
        return npcs

    async def generate_characters_batch(
        self,
        ctx: Optional[GameContext],
        world_setting: str,
        role_type: str,
        count: int,
        genre: str = "fantasy",
        power_level: str = "medium"
    ) -> List[dict]:
        if count <= 0:
            return []
            
        list_prompt = CHARACTER_LIST_GENERATION_PROMPT.format(
            count=count,
            role_type=role_type,
            role_type_cn=ROLE_TYPE_CN.get(role_type, role_type),
            world_setting=world_setting,
            genre=genre,
            power_level=power_level,
            role_description=ROLE_DESCRIPTIONS.get(role_type, "")
        )

        system_prompt_list = "你是一个专业的角色设计师，擅长创造生动有趣的角色名录。请严格按照JSON数组格式返回结果。"

        response_list = await self.llm_adapter.generate_json(
            ctx=ctx,
            prompt=list_prompt,
            system_prompt=system_prompt_list,
            timeout=120,
            method_name=f"generate_{role_type}_list",
        )
        try:
            characters_list = response_list
        except Exception as e:
            logger.warning("%s 名录 JSON解析失败，尝试修复: %s", role_type, str(e)[:200])
            characters_list = self._try_fix_truncated_json(str(response_list))

        if not characters_list or not isinstance(characters_list, list):
            return []
            
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_character_detail(char_basic):
            async with semaphore:
                detail_prompt = CHARACTER_DETAIL_GENERATION_PROMPT.format(
                    world_setting=world_setting,
                    genre=genre,
                    power_level=power_level,
                    role_type_cn=ROLE_TYPE_CN.get(role_type, role_type),
                    role_description=ROLE_DESCRIPTIONS.get(role_type, ""),
                    character_name=char_basic.get('name', '未知'),
                    character_title=char_basic.get('title', ''),
                    character_description=char_basic.get('description', ''),
                    role_type=role_type,
                    importance=ROLE_IMPORTANCE.get(role_type, 1)
                )
                system_prompt_detail = "你是一个专业的角色设计师。请严格按照JSON格式返回角色详细设定。"
                try:
                    detail_data = await self.llm_adapter.generate_json(
                        ctx=ctx,
                        prompt=detail_prompt,
                        system_prompt=system_prompt_detail,
                        timeout=180,
                        method_name=f"generate_{role_type}_detail",
                    )
                    if isinstance(detail_data, dict):
                        return detail_data
                except Exception as e:
                    logger.warning("生成角色 %s 详细信息失败: %s", char_basic.get('name'), e)
                return None

        logger.info("开始并发生成 %s 个 %s 详细信息...", len(characters_list[:count]), role_type)
        details_results = await asyncio.gather(*(fetch_character_detail(char) for char in characters_list[:count]))
        
        characters = []
        for char in details_results:
            if not char:
                continue
            char['id'] = f"char_{uuid.uuid4().hex[:8]}"
            char['generated_by'] = "auto"
            char['created_at'] = datetime.now().isoformat()
            char['updated_at'] = datetime.now().isoformat()
            if 'attributes' not in char:
                char['attributes'] = AttributesModel().dict()
            if 'appearance' not in char:
                char['appearance'] = AppearanceModel().dict()
            if 'background' not in char:
                char['background'] = BackgroundModel().dict()
            if 'personality' not in char:
                char['personality'] = PersonalityModel().dict()
            if 'status' not in char:
                char['status'] = StatusModel().dict()
            if 'skills' not in char:
                char['skills'] = []
            if 'tags' not in char:
                char['tags'] = []
            characters.append(char)

        return characters

    async def generate_all_characters(
        self, ctx: Optional[GameContext], config: CharacterGenerationConfig
    ) -> List[dict]:
        all_characters = []

        results = await asyncio.gather(
            self.generate_characters_batch(
                ctx,
                config.world_setting, "protagonist", config.protagonist_count,
                config.genre, config.power_level
            ),
            self.generate_characters_batch(
                ctx,
                config.world_setting, "antagonist", config.antagonist_count,
                config.genre, config.power_level
            ),
            self.generate_characters_batch(
                ctx,
                config.world_setting, "supporting", config.supporting_count,
                config.genre, config.power_level
            ),
            self.generate_characters_batch(
                ctx,
                config.world_setting, "npc", config.npc_count,
                config.genre, config.power_level
            )
        )
        
        for batch in results:
            if batch:
                all_characters.extend(batch)

        return all_characters

    async def generate_relations(
        self, ctx: Optional[GameContext], characters: List[dict], world_setting: str
    ) -> List[dict]:
        char_summaries = []
        for char in characters:
            char_summaries.append({
                "id": char['id'],
                "name": char['name'],
                "role_type": char.get('role_type', 'npc'),
                "affiliation": char.get('background', {}).get('affiliation', '')
            })

        prompt = RELATION_GENERATION_PROMPT.format(
            characters_json=json.dumps(char_summaries, ensure_ascii=False, indent=2),
            world_setting=world_setting
        )

        system_prompt = "你是一个关系网络设计师，擅长构建复杂的人物关系网络。请严格按照JSON格式返回结果。"

        relations = await self.llm_adapter.generate_json(
            ctx=ctx,
            prompt=prompt,
            system_prompt=system_prompt,
            timeout=360,
            method_name="generate_relations",
        )

        name_to_id = {char['name']: char['id'] for char in characters}

        valid_relations = []
        for rel in relations:
            source_name = rel.get('source_name', '')
            target_name = rel.get('target_name', '')

            source_id = name_to_id.get(source_name)
            target_id = name_to_id.get(target_name)

            if source_id and target_id and source_id != target_id:
                valid_relations.append({
                    "id": f"rel_{uuid.uuid4().hex[:8]}",
                    "source_id": source_id,
                    "target_id": target_id,
                    "relation_type": rel.get('relation_type', 'neutral'),
                    "strength": rel.get('strength', 50),
                    "trust": rel.get('trust', 50),
                    "description": rel.get('description', ''),
                    "since_chapter": 0,
                    "events": [],
                    "is_public": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })

        return valid_relations

    def update_character_state(
        self, ctx: Optional[GameContext], char_id: str, effects: List[Dict]
    ) -> bool:
        char = self.character_repository.load(ctx, char_id)
        if not char:
            return False

        for effect in effects:
            effect_type = effect.get('effect_type')
            target = effect.get('target')
            value = effect.get('value')

            if effect_type == "attribute":
                if 'attributes' not in char:
                    char['attributes'] = AttributesModel().dict()
                char['attributes'][target] = value
            elif effect_type == "status":
                if 'status' not in char:
                    char['status'] = StatusModel().dict()
                char['status'][target] = value
            elif effect_type == "condition":
                if 'status' not in char:
                    char['status'] = StatusModel().dict()
                if 'conditions' not in char['status']:
                    char['status']['conditions'] = []
                if value:
                    if target not in char['status']['conditions']:
                        char['status']['conditions'].append(target)
                else:
                    conditions = char['status'].get('conditions', [])
                    char['status']['conditions'] = [c for c in conditions if c != target]

        self.character_repository.save(ctx, char)
        return True

    def batch_update(self, ctx: Optional[GameContext], updates: List[Dict]) -> int:
        updated_count = 0
        for update in updates:
            char_id = update.get('character_id')
            effects = update.get('effects', [])
            if self.update_character_state(ctx, char_id, effects):
                updated_count += 1
        return updated_count

    def create_snapshot(self, ctx: GameContext, chapter: int) -> str:
        characters = self.character_repository.load_all(ctx)
        relations = self.relation_repository.load_all(ctx)

        snapshot = {
            'chapter': chapter,
            'timestamp': datetime.now().isoformat(),
            'characters': characters,
            'relations': relations
        }

        return self.snapshot_repository.save(ctx, chapter, snapshot)

    def get_character_context(
        self, ctx: Optional[GameContext], character_ids: List[str]
    ) -> str:
        characters = self.character_repository.load_all(ctx)
        relations = self.relation_repository.load_all(ctx)

        selected_chars = [c for c in characters if c['id'] in character_ids]

        if not selected_chars:
            return ""

        context_parts = ["## 当前场景角色\n"]
        for char in selected_chars:
            context_parts.append(f"### {char['name']}")
            if char.get('title'):
                context_parts.append(f"称号: {char['title']}")
            if char.get('description'):
                context_parts.append(f"描述: {char['description']}")
            if char.get('personality', {}).get('traits'):
                context_parts.append(f"性格: {', '.join(char['personality']['traits'])}")
            if char.get('personality', {}).get('dialogue_style'):
                context_parts.append(f"对话风格: {char['personality']['dialogue_style']}")
            if char.get('status', {}).get('current_state'):
                context_parts.append(f"当前状态: {char['status']['current_state']}")
            if char.get('status', {}).get('mood'):
                context_parts.append(f"心情: {char['status']['mood']}")

        char_ids_set = set(character_ids)
        relevant_relations = [r for r in relations if r['source_id'] in char_ids_set or r['target_id'] in char_ids_set]

        if relevant_relations:
            context_parts.append("\n## 角色关系\n")
            for rel in relevant_relations:
                source = next((c for c in characters if c['id'] == rel['source_id']), None)
                target = next((c for c in characters if c['id'] == rel['target_id']), None)
                if source and target:
                    rel_type = RELATION_TYPES.get(rel['relation_type'], RELATION_TYPES['neutral'])
                    context_parts.append(f"- {source['name']} → {target['name']}: {rel_type['name']} (强度: {rel['strength']})")

        context = "\n".join(context_parts)
        return context

    def get_character_graph(self, ctx: Optional[GameContext]) -> Dict:
        characters = self.character_repository.load_all(ctx)
        relations = self.relation_repository.load_all(ctx)

        nodes = []
        for char in characters:
            nodes.append({
                'id': char['id'],
                'name': char['name'],
                'title': char.get('title', ''),
                'avatar': char.get('avatar', ''),
                'status': char.get('status', {}).get('current_state', 'active')
            })

        edges = []
        for rel in relations:
            rel_type = RELATION_TYPES.get(rel['relation_type'], RELATION_TYPES['neutral'])
            edges.append({
                'id': rel['id'],
                'source': rel['source_id'],
                'target': rel['target_id'],
                'type': rel['relation_type'],
                'typeName': rel_type['name'],
                'color': rel_type['color'],
                'icon': rel_type['icon'],
                'strength': rel.get('strength', 50),
                'description': rel.get('description', '')
            })

        return {
            'nodes': nodes,
            'edges': edges,
            'relationTypes': RELATION_TYPES
        }
