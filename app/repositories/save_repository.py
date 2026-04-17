import json
import os
from typing import List, Optional

from app.game_context import GameContext
from app.repositories.base import FileRepositoryPaths
from app.utils.atomic_io import atomic_write_json
from app.utils.history_round_count import narrative_round_count_from_history


class SaveRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def list_saves(self, ctx: GameContext) -> List[dict]:
        saves_dir = self.paths.saves_dir(ctx)
        if not os.path.exists(saves_dir):
            return []
        saves = []
        for filename in os.listdir(saves_dir):
            if filename.startswith("save_") and filename.endswith(".json"):
                with open(os.path.join(saves_dir, filename), "r", encoding="utf-8") as f:
                    saves.append(json.load(f))
        return sorted(saves, key=lambda item: item.get("timestamp", ""), reverse=True)

    def save_game_state(self, ctx: GameContext, slot_id: str, data: dict) -> str:
        path = self.paths.save_path(ctx, slot_id)
        atomic_write_json(path, data)
        return path

    def load_game_state(self, ctx: Optional[GameContext], slot_id: str) -> Optional[dict]:
        if ctx is None:
            return None
        path = self.paths.save_path(ctx, slot_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def delete_game_state(self, ctx: GameContext, slot_id: str) -> bool:
        path = self.paths.save_path(ctx, slot_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def save_history(self, ctx: GameContext, history: List[dict]) -> None:
        atomic_write_json(self.paths.history_path(ctx), history)

    def load_history(self, ctx: Optional[GameContext]) -> List[dict]:
        if ctx is None:
            return []
        path = self.paths.history_path(ctx)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_round_count(self, ctx: Optional[GameContext]) -> int:
        return narrative_round_count_from_history(self.load_history(ctx))
