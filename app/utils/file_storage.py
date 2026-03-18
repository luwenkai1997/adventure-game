import os
import json
import uuid
from typing import Optional, List
from datetime import datetime
from app.config import (
    BASE_DIR,
    MEMORY_DIR,
    CHARACTERS_DIR,
    RELATIONS_FILE,
    DATA_DIR,
    NOVELS_DIR,
    SNAPSHOTS_DIR,
)


def get_or_create_characters_dir() -> str:
    if not os.path.exists(CHARACTERS_DIR):
        os.makedirs(CHARACTERS_DIR)
    return CHARACTERS_DIR


def get_or_create_memory_dir() -> str:
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)
    return MEMORY_DIR


def get_or_create_data_dir() -> str:
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    return DATA_DIR


def get_or_create_novels_dir() -> str:
    if not os.path.exists(NOVELS_DIR):
        os.makedirs(NOVELS_DIR)
    return NOVELS_DIR


def get_or_create_snapshots_dir() -> str:
    if not os.path.exists(SNAPSHOTS_DIR):
        os.makedirs(SNAPSHOTS_DIR)
    return SNAPSHOTS_DIR


def save_memory(world_setting: str, story_summary: str = "") -> str:
    memory_dir = get_or_create_memory_dir()
    memory_path = os.path.join(memory_dir, 'memory.md')
    content = f"""# 游戏记忆文档

## 世界观设定
{world_setting}

## 故事概要
{story_summary}

## 主要角色
（待补充）

## 故事流程
（待补充）

## 当前状态
（待补充）
"""
    with open(memory_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return memory_path


def save_memory_text(content: str) -> str:
    memory_dir = get_or_create_memory_dir()
    memory_path = os.path.join(memory_dir, 'memory.md')
    with open(memory_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return memory_path


def load_memory() -> str:
    memory_dir = get_or_create_memory_dir()
    memory_path = os.path.join(memory_dir, 'memory.md')
    if os.path.exists(memory_path):
        with open(memory_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def load_characters() -> List[dict]:
    get_or_create_characters_dir()
    characters = []
    for filename in os.listdir(CHARACTERS_DIR):
        if filename.endswith('.json') and filename != 'relations.json':
            filepath = os.path.join(CHARACTERS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                characters.append(json.load(f))
    return characters


def save_character(character: dict) -> str:
    get_or_create_characters_dir()
    if not character.get('id'):
        character['id'] = f"char_{uuid.uuid4().hex[:8]}"
    character['updated_at'] = datetime.now().isoformat()
    if 'created_at' not in character:
        character['created_at'] = character['updated_at']

    filepath = os.path.join(CHARACTERS_DIR, f"{character['id']}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(character, f, ensure_ascii=False, indent=2)
    return character['id']


def load_character(char_id: str) -> Optional[dict]:
    get_or_create_characters_dir()
    filepath = os.path.join(CHARACTERS_DIR, f"{char_id}.json")
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def delete_character(char_id: str) -> bool:
    get_or_create_characters_dir()
    filepath = os.path.join(CHARACTERS_DIR, f"{char_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def save_characters_batch(characters: List[dict]) -> int:
    get_or_create_characters_dir()
    saved_count = 0
    for char in characters:
        if save_character(char):
            saved_count += 1
    return saved_count


def load_relations() -> List[dict]:
    get_or_create_characters_dir()
    if os.path.exists(RELATIONS_FILE):
        with open(RELATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_relations(relations: List[dict]) -> None:
    get_or_create_characters_dir()
    with open(RELATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)


def add_relation(relation: dict) -> dict:
    relations = load_relations()
    if not relation.get('id'):
        relation['id'] = f"rel_{uuid.uuid4().hex[:8]}"
    relation['updated_at'] = datetime.now().isoformat()
    if 'created_at' not in relation:
        relation['created_at'] = relation['updated_at']
    relations.append(relation)
    save_relations(relations)
    return relation


def update_relation(rel_id: str, updates: dict) -> Optional[dict]:
    relations = load_relations()
    for i, rel in enumerate(relations):
        if rel['id'] == rel_id:
            relations[i].update(updates)
            relations[i]['updated_at'] = datetime.now().isoformat()
            save_relations(relations)
            return relations[i]
    return None


def delete_relation(rel_id: str) -> bool:
    relations = load_relations()
    for i, rel in enumerate(relations):
        if rel['id'] == rel_id:
            relations.pop(i)
            save_relations(relations)
            return True
    return False
