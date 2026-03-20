import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List


GAMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "games")


def get_games_dir() -> str:
    if not os.path.exists(GAMES_DIR):
        os.makedirs(GAMES_DIR)
    return GAMES_DIR


def generate_game_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"game_{timestamp}"


def create_game_structure(game_id: Optional[str] = None, world_setting: str = "") -> Dict[str, str]:
    if game_id is None:
        game_id = generate_game_id()
    
    game_dir = os.path.join(get_games_dir(), game_id)
    
    subdirs = ["memory", "novel", "character", "player", "saves", "snapshots"]
    paths = {"game_dir": game_dir}
    
    for subdir in subdirs:
        subdir_path = os.path.join(game_dir, subdir)
        os.makedirs(subdir_path, exist_ok=True)
        paths[f"{subdir}_dir"] = subdir_path
    
    game_info = {
        "game_id": game_id,
        "created_at": datetime.now().isoformat(),
        "world_setting": world_setting,
        "status": "active"
    }
    
    game_info_path = os.path.join(game_dir, "game_info.json")
    with open(game_info_path, "w", encoding="utf-8") as f:
        json.dump(game_info, f, ensure_ascii=False, indent=2)
    paths["game_info"] = game_info_path
    
    return paths


def list_all_games() -> List[Dict[str, Any]]:
    games_dir = get_games_dir()
    games = []
    
    for game_name in os.listdir(games_dir):
        game_path = os.path.join(games_dir, game_name)
        if os.path.isdir(game_path) and game_name.startswith("game_"):
            game_info_path = os.path.join(game_path, "game_info.json")
            if os.path.exists(game_info_path):
                with open(game_info_path, "r", encoding="utf-8") as f:
                    game_info = json.load(f)
                games.append(game_info)
            else:
                games.append({
                    "game_id": game_name,
                    "created_at": "unknown",
                    "world_setting": "",
                    "status": "unknown"
                })
    
    return sorted(games, key=lambda x: x.get("created_at", ""), reverse=True)


def get_current_game_id() -> Optional[str]:
    games = list_all_games()
    if games:
        return games[0]["game_id"]
    return None


def get_game_dir(game_id: str) -> str:
    game_dir = os.path.join(get_games_dir(), game_id)
    if not os.path.exists(game_dir):
        raise FileNotFoundError(f"游戏目录不存在: {game_id}")
    return game_dir


def get_memory_dir(game_id: str) -> str:
    return os.path.join(get_game_dir(game_id), "memory")


def get_novel_dir(game_id: str) -> str:
    return os.path.join(get_game_dir(game_id), "novel")


def get_character_dir(game_id: str) -> str:
    return os.path.join(get_game_dir(game_id), "character")


def get_player_dir(game_id: str) -> str:
    return os.path.join(get_game_dir(game_id), "player")


def get_saves_dir(game_id: str) -> str:
    return os.path.join(get_game_dir(game_id), "saves")


def get_snapshots_dir(game_id: str) -> str:
    return os.path.join(get_game_dir(game_id), "snapshots")


def update_game_info(game_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    game_dir = get_game_dir(game_id)
    game_info_path = os.path.join(game_dir, "game_info.json")
    
    if os.path.exists(game_info_path):
        with open(game_info_path, "r", encoding="utf-8") as f:
            game_info = json.load(f)
    else:
        game_info = {"game_id": game_id}
    
    game_info.update(updates)
    game_info["updated_at"] = datetime.now().isoformat()
    
    with open(game_info_path, "w", encoding="utf-8") as f:
        json.dump(game_info, f, ensure_ascii=False, indent=2)
    
    return game_info


def get_game_info(game_id: str) -> Optional[Dict[str, Any]]:
    game_dir = get_game_dir(game_id)
    game_info_path = os.path.join(game_dir, "game_info.json")
    
    if os.path.exists(game_info_path):
        with open(game_info_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def delete_game(game_id: str) -> bool:
    import shutil
    game_dir = os.path.join(get_games_dir(), game_id)
    if os.path.exists(game_dir):
        shutil.rmtree(game_dir)
        return True
    return False
