import os
import json
import uuid
from typing import Optional, List, Dict
from datetime import datetime
from app.config import (
    CHARACTER_GENERATION_PROMPT,
    RELATION_GENERATION_PROMPT,
    ROLE_DESCRIPTIONS,
    ROLE_TYPE_CN,
    ROLE_IMPORTANCE,
    RELATION_TYPES,
    SNAPSHOTS_DIR,
    BASE_DIR,
)
from app.models.character import (
    AttributesModel,
    AppearanceModel,
    BackgroundModel,
    PersonalityModel,
    StatusModel,
    CharacterGenerationConfig,
    StateEffect,
)
from app.utils.file_storage import (
    load_characters,
    save_character,
    load_character,
    delete_character,
    save_characters_batch,
    load_relations,
    save_relations,
    add_relation,
    update_relation,
    delete_relation,
    get_or_create_snapshots_dir,
)
from app.utils.llm_client import call_llm, parse_json_response


class CharacterService:
    def __init__(self):
        pass

    def generate_characters_batch(
        self,
        world_setting: str,
        role_type: str,
        count: int,
        genre: str = "fantasy",
        power_level: str = "medium"
    ) -> List[dict]:
        prompt = CHARACTER_GENERATION_PROMPT.format(
            count=count,
            role_type=role_type,
            role_type_cn=ROLE_TYPE_CN.get(role_type, role_type),
            world_setting=world_setting,
            genre=genre,
            power_level=power_level,
            role_description=ROLE_DESCRIPTIONS.get(role_type, ""),
            importance=ROLE_IMPORTANCE.get(role_type, 1)
        )

        system_prompt = "你是一个专业的角色设计师，擅长创造生动有趣的角色。请严格按照JSON格式返回结果。"

        response = call_llm(prompt, system_prompt, timeout=180)
        characters = parse_json_response(response)

        for char in characters:
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

        return characters

    def generate_all_characters(self, config: CharacterGenerationConfig) -> List[dict]:
        all_characters = []

        protagonists = self.generate_characters_batch(
            config.world_setting, "protagonist", config.protagonist_count,
            config.genre, config.power_level
        )
        all_characters.extend(protagonists)

        antagonists = self.generate_characters_batch(
            config.world_setting, "antagonist", config.antagonist_count,
            config.genre, config.power_level
        )
        all_characters.extend(antagonists)

        supporting = self.generate_characters_batch(
            config.world_setting, "supporting", config.supporting_count,
            config.genre, config.power_level
        )
        all_characters.extend(supporting)

        npcs = self.generate_characters_batch(
            config.world_setting, "npc", config.npc_count,
            config.genre, config.power_level
        )
        all_characters.extend(npcs)

        return all_characters

    def generate_relations(self, characters: List[dict], world_setting: str) -> List[dict]:
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

        response = call_llm(prompt, system_prompt, timeout=120)
        relations = parse_json_response(response)

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

    def update_character_state(self, char_id: str, effects: List[Dict]) -> bool:
        char = load_character(char_id)
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

        save_character(char)
        return True

    def batch_update(self, updates: List[Dict]) -> int:
        updated_count = 0
        for update in updates:
            char_id = update.get('character_id')
            effects = update.get('effects', [])
            if self.update_character_state(char_id, effects):
                updated_count += 1
        return updated_count

    def create_snapshot(self, chapter: int) -> str:
        characters = load_characters()
        relations = load_relations()

        get_or_create_snapshots_dir()

        snapshot = {
            'chapter': chapter,
            'timestamp': datetime.now().isoformat(),
            'characters': characters,
            'relations': relations
        }

        snapshot_path = os.path.join(SNAPSHOTS_DIR, f'chapter_{chapter:03d}.json')
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        return snapshot_path

    def get_character_context(self, character_ids: List[str]) -> str:
        characters = load_characters()
        relations = load_relations()

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

    def get_character_graph(self) -> Dict:
        characters = load_characters()
        relations = load_relations()

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
