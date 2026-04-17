import os
import json
import uuid
from typing import Optional, List, Dict
from datetime import datetime
from app.request_context import get_current_session_id
from app.utils.game_manager import (
    get_current_game_id,
    get_memory_dir,
    get_character_dir,
    get_novel_dir,
    get_player_dir,
    get_saves_dir,
    get_snapshots_dir,
    create_game_structure,
)
from app.config import BASE_DIR
from app.utils.history_round_count import narrative_round_count_from_history


_session_game_map: Dict[str, Optional[str]] = {}

SESSION_STORE_PATH = os.path.join(BASE_DIR, "data", "session_games.json")


def load_session_games_from_disk() -> None:
    """Restore session → active game mapping after server restart."""
    global _session_game_map
    try:
        if os.path.exists(SESSION_STORE_PATH):
            with open(SESSION_STORE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(k, str) and (v is None or isinstance(v, str)):
                        _session_game_map[k] = v
    except Exception:
        pass


def _persist_session_games() -> None:
    try:
        os.makedirs(os.path.dirname(SESSION_STORE_PATH), exist_ok=True)
        with open(SESSION_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(_session_game_map, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_session_game_map() -> Dict[str, Optional[str]]:
    return _session_game_map


def set_current_game(game_id: str) -> None:
    session_id = get_current_session_id()
    if session_id:
        _session_game_map[session_id] = game_id
    else:
        _session_game_map["default"] = game_id
    _persist_session_games()


def get_current_game() -> Optional[str]:
    session_id = get_current_session_id()
    
    def is_valid_game(g_id: Optional[str]) -> bool:
        if not g_id:
            return False
        from app.utils.game_manager import get_games_dir
        return os.path.exists(os.path.join(get_games_dir(), g_id))

    game_id = None
    if session_id and session_id in _session_game_map:
        g_id = _session_game_map[session_id]
        if is_valid_game(g_id):
            game_id = g_id
        else:
            del _session_game_map[session_id]
            _persist_session_games()
            
    if not game_id and "default" in _session_game_map:
        g_id = _session_game_map["default"]
        if is_valid_game(g_id):
            game_id = g_id
        else:
            del _session_game_map["default"]
            _persist_session_games()
            
    return game_id or get_current_game_id()


def require_game_id() -> str:
    game_id = get_current_game()
    if game_id is None:
        raise RuntimeError("没有活动的游戏，请先创建或加载游戏")
    return game_id


def init_new_game(world_setting: str = "") -> dict:
    paths = create_game_structure(world_setting=world_setting)
    game_id = paths["game_dir"].split("/")[-1]
    set_current_game(game_id)
    return paths


def get_or_create_characters_dir() -> str:
    game_id = require_game_id()
    char_dir = get_character_dir(game_id)
    if not os.path.exists(char_dir):
        os.makedirs(char_dir)
    return char_dir


def get_or_create_memory_dir() -> str:
    game_id = require_game_id()
    memory_dir = get_memory_dir(game_id)
    if not os.path.exists(memory_dir):
        os.makedirs(memory_dir)
    return memory_dir


def get_or_create_novels_dir() -> str:
    game_id = require_game_id()
    novels_dir = get_novel_dir(game_id)
    if not os.path.exists(novels_dir):
        os.makedirs(novels_dir)
    return novels_dir


def get_or_create_snapshots_dir() -> str:
    game_id = require_game_id()
    snapshots_dir = get_snapshots_dir(game_id)
    if not os.path.exists(snapshots_dir):
        os.makedirs(snapshots_dir)
    return snapshots_dir


def get_or_create_player_dir() -> str:
    game_id = require_game_id()
    player_dir = get_player_dir(game_id)
    if not os.path.exists(player_dir):
        os.makedirs(player_dir)
    return player_dir


def get_or_create_saves_dir() -> str:
    game_id = require_game_id()
    saves_dir = get_saves_dir(game_id)
    if not os.path.exists(saves_dir):
        os.makedirs(saves_dir)
    return saves_dir


def save_memory(world_setting: str, story_summary: str = "") -> str:
    memory_dir = get_or_create_memory_dir()
    memory_path = os.path.join(memory_dir, "memory.md")
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
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write(content)
    return memory_path


def save_memory_text(content: str) -> str:
    memory_dir = get_or_create_memory_dir()
    memory_path = os.path.join(memory_dir, "memory.md")
    with open(memory_path, "w", encoding="utf-8") as f:
        f.write(content)
    return memory_path


def load_memory() -> str:
    try:
        memory_dir = get_or_create_memory_dir()
        memory_path = os.path.join(memory_dir, "memory.md")
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                return f.read()
    except RuntimeError:
        pass
    return ""


def load_characters() -> List[dict]:
    try:
        get_or_create_characters_dir()
        game_id = require_game_id()
        char_dir = get_character_dir(game_id)
        characters = []
        for filename in os.listdir(char_dir):
            if filename.endswith(".json") and filename != "relations.json":
                filepath = os.path.join(char_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    characters.append(json.load(f))
        return characters
    except RuntimeError:
        return []


def save_character(character: dict) -> str:
    get_or_create_characters_dir()
    if not character.get("id"):
        character["id"] = f"char_{uuid.uuid4().hex[:8]}"
    character["updated_at"] = datetime.now().isoformat()
    if "created_at" not in character:
        character["created_at"] = character["updated_at"]

    game_id = require_game_id()
    char_dir = get_character_dir(game_id)
    filepath = os.path.join(char_dir, f"{character['id']}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(character, f, ensure_ascii=False, indent=2)
    return character["id"]


def load_character(char_id: str) -> Optional[dict]:
    from app.utils.path_security import validate_char_id

    cid = validate_char_id(char_id)
    get_or_create_characters_dir()
    game_id = require_game_id()
    char_dir = get_character_dir(game_id)
    filepath = os.path.join(char_dir, f"{cid}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def delete_character(char_id: str) -> bool:
    from app.utils.path_security import validate_char_id

    cid = validate_char_id(char_id)
    get_or_create_characters_dir()
    game_id = require_game_id()
    char_dir = get_character_dir(game_id)
    filepath = os.path.join(char_dir, f"{cid}.json")
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


def get_relations_file() -> str:
    game_id = require_game_id()
    char_dir = get_character_dir(game_id)
    return os.path.join(char_dir, "relations.json")


def load_relations() -> List[dict]:
    try:
        get_or_create_characters_dir()
        relations_file = get_relations_file()
        if os.path.exists(relations_file):
            with open(relations_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except RuntimeError:
        pass
    return []


def save_relations(relations: List[dict]) -> None:
    get_or_create_characters_dir()
    relations_file = get_relations_file()
    with open(relations_file, "w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)


def add_relation(relation: dict) -> dict:
    relations = load_relations()
    if not relation.get("id"):
        relation["id"] = f"rel_{uuid.uuid4().hex[:8]}"
    relation["updated_at"] = datetime.now().isoformat()
    if "created_at" not in relation:
        relation["created_at"] = relation["updated_at"]
    relations.append(relation)
    save_relations(relations)
    return relation


def update_relation(rel_id: str, updates: dict) -> Optional[dict]:
    relations = load_relations()
    for i, rel in enumerate(relations):
        if rel["id"] == rel_id:
            relations[i].update(updates)
            relations[i]["updated_at"] = datetime.now().isoformat()
            save_relations(relations)
            return relations[i]
    return None


def delete_relation(rel_id: str) -> bool:
    relations = load_relations()
    for i, rel in enumerate(relations):
        if rel["id"] == rel_id:
            relations.pop(i)
            save_relations(relations)
            return True
    return False


def save_player(player: dict) -> str:
    get_or_create_player_dir()
    player["updated_at"] = datetime.now().isoformat()
    if "created_at" not in player:
        player["created_at"] = player["updated_at"]

    game_id = require_game_id()
    player_dir = get_player_dir(game_id)
    filepath = os.path.join(player_dir, "player.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=2)
    return player.get("id", "player")


def load_player() -> Optional[dict]:
    try:
        get_or_create_player_dir()
        game_id = require_game_id()
        player_dir = get_player_dir(game_id)
        filepath = os.path.join(player_dir, "player.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except RuntimeError:
        pass
    return None


def delete_player() -> bool:
    get_or_create_player_dir()
    game_id = require_game_id()
    player_dir = get_player_dir(game_id)
    filepath = os.path.join(player_dir, "player.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def list_saves() -> List[dict]:
    get_or_create_saves_dir()
    game_id = require_game_id()
    saves_dir = get_saves_dir(game_id)
    saves = []
    for filename in os.listdir(saves_dir):
        if filename.startswith("save_") and filename.endswith(".json"):
            filepath = os.path.join(saves_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                saves.append(json.load(f))
    return sorted(saves, key=lambda x: x.get("timestamp", ""), reverse=True)


def save_game_state(slot_id: str, data: dict) -> str:
    get_or_create_saves_dir()
    game_id = require_game_id()
    saves_dir = get_saves_dir(game_id)
    filepath = os.path.join(saves_dir, f"save_{slot_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def load_game_state(slot_id: str) -> Optional[dict]:
    get_or_create_saves_dir()
    game_id = require_game_id()
    saves_dir = get_saves_dir(game_id)
    filepath = os.path.join(saves_dir, f"save_{slot_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def delete_game_save(slot_id: str) -> bool:
    get_or_create_saves_dir()
    game_id = require_game_id()
    saves_dir = get_saves_dir(game_id)
    filepath = os.path.join(saves_dir, f"save_{slot_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def save_history(history: List[dict]) -> None:
    get_or_create_saves_dir()
    game_id = require_game_id()
    saves_dir = get_saves_dir(game_id)
    filepath = os.path.join(saves_dir, "history.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_history() -> List[dict]:
    try:
        get_or_create_saves_dir()
        game_id = require_game_id()
        saves_dir = get_saves_dir(game_id)
        filepath = os.path.join(saves_dir, "history.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except RuntimeError:
        pass
    return []


def get_novel_path(novel_folder: str) -> str:
    game_id = require_game_id()
    return os.path.join(get_novel_dir(game_id), novel_folder)


def get_snapshot_path(chapter: int) -> str:
    game_id = require_game_id()
    snapshots_dir = get_snapshots_dir(game_id)
    return os.path.join(snapshots_dir, f"chapter_{chapter:03d}.json")


def get_game_round_count() -> int:
    """Return how many narrative rounds the active game has progressed.

    ``history.json`` is capped at ``MAX_HISTORY_STEPS`` entries for undo, so
    ``len(history)`` is **not** the total round count. We use the snapshot with
    the longest ``logs`` array (full cumulative log) and count main entries.
    """
    return narrative_round_count_from_history(load_history())
