import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.game_context import GameContext
from app.repositories.base import FileRepositoryPaths
from app.utils.atomic_io import atomic_write_json, atomic_write_text
from app.utils.path_security import validate_game_id


class GameRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def generate_game_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"game_{timestamp}"

    def exists(self, game_id: str) -> bool:
        try:
            path = self.paths.game_dir(game_id)
        except Exception:
            return False
        return os.path.exists(path)

    def create(self, world_setting: str = "", game_id: Optional[str] = None) -> Dict[str, str]:
        new_game_id = validate_game_id(game_id) if game_id else self.generate_game_id()
        game_dir = self.paths.game_dir(new_game_id)
        subdirs = ["memory", "novel", "character", "player", "saves", "snapshots"]
        paths = {"game_dir": game_dir}

        os.makedirs(game_dir, exist_ok=True)
        for subdir in subdirs:
            subdir_path = os.path.join(game_dir, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            paths[f"{subdir}_dir"] = subdir_path

        game_info = {
            "game_id": new_game_id,
            "created_at": datetime.now().isoformat(),
            "world_setting": world_setting,
            "status": "active",
        }
        game_info_path = self.paths.game_info_path(new_game_id)
        atomic_write_json(game_info_path, game_info)
        paths["game_info"] = game_info_path
        return paths

    def list_all(self) -> List[Dict[str, Any]]:
        games = []
        for game_name in os.listdir(self.paths.games_dir):
            game_path = os.path.join(self.paths.games_dir, game_name)
            if os.path.isdir(game_path) and game_name.startswith("game_"):
                game_info = self.get_game_info(game_name)
                if game_info:
                    games.append(game_info)
                else:
                    games.append(
                        {
                            "game_id": game_name,
                            "created_at": "unknown",
                            "world_setting": "",
                            "status": "unknown",
                        }
                    )
        return sorted(games, key=lambda item: item.get("created_at", ""), reverse=True)

    def get_latest_game_id(self) -> Optional[str]:
        games = self.list_all()
        if games:
            return games[0]["game_id"]
        return None

    def get_game_info(self, game_id: str) -> Optional[Dict[str, Any]]:
        game_info_path = self.paths.game_info_path(game_id)
        if os.path.exists(game_info_path):
            with open(game_info_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def update_game_info(self, game_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        game_info = self.get_game_info(game_id) or {"game_id": validate_game_id(game_id)}
        game_info.update(updates)
        game_info["updated_at"] = datetime.now().isoformat()
        atomic_write_json(self.paths.game_info_path(game_id), game_info)
        return game_info

    def delete(self, game_id: str) -> bool:
        game_dir = self.paths.game_dir(game_id)
        if os.path.exists(game_dir):
            shutil.rmtree(game_dir)
            return True
        return False


class MemoryRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def save_initial(
        self, ctx: GameContext, world_setting: str, story_summary: str = ""
    ) -> str:
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
        return self.save_text(ctx, content)

    def save_text(self, ctx: GameContext, content: str) -> str:
        path = self.paths.memory_path(ctx)
        atomic_write_text(path, content)
        return path

    def load_text(self, ctx: Optional[GameContext]) -> str:
        if ctx is None:
            return ""
        path = self.paths.memory_path(ctx)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""


class PlayerRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def save(self, ctx: GameContext, player: dict) -> str:
        player["updated_at"] = datetime.now().isoformat()
        if "created_at" not in player:
            player["created_at"] = player["updated_at"]
        path = self.paths.player_path(ctx)
        atomic_write_json(path, player)
        return player.get("id", "player")

    def load(self, ctx: Optional[GameContext]) -> Optional[dict]:
        if ctx is None:
            return None
        path = self.paths.player_path(ctx)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def delete(self, ctx: GameContext) -> bool:
        path = self.paths.player_path(ctx)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
