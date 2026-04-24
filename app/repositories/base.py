import os
from typing import Optional

from app.config import BASE_DIR
from app.game_context import GameContext
from app.utils.path_security import (
    assert_path_under_root,
    validate_char_id,
    validate_game_id,
    validate_novel_folder,
    validate_slot_id,
)


class FileRepositoryPaths:
    def __init__(self, base_dir: str = BASE_DIR):
        self.base_dir = base_dir
        self.games_dir = os.path.join(base_dir, "games")
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.games_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

    def session_store_path(self) -> str:
        return os.path.join(self.data_dir, "session_games.json")

    def _validate_ctx(self, ctx: Optional[GameContext]) -> GameContext:
        if ctx is None:
            raise RuntimeError("没有活动的游戏，请先创建或加载游戏")
        return ctx

    def game_dir(self, game_id: str) -> str:
        gid = validate_game_id(game_id)
        root = os.path.realpath(self.games_dir)
        path = os.path.join(root, gid)
        assert_path_under_root(path, root)
        return path

    def existing_game_dir(self, game_id: str) -> str:
        path = self.game_dir(game_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"游戏目录不存在: {game_id}")
        return path

    def game_dir_from_ctx(self, ctx: Optional[GameContext]) -> str:
        return self.existing_game_dir(self._validate_ctx(ctx).game_id)

    def game_info_path(self, game_id: str) -> str:
        return os.path.join(self.game_dir(game_id), "game_info.json")

    def memory_dir(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.game_dir_from_ctx(ctx), "memory")

    def memory_path(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.memory_dir(ctx), "memory.md")

    def character_dir(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.game_dir_from_ctx(ctx), "character")

    def character_path(self, ctx: Optional[GameContext], char_id: str) -> str:
        cid = validate_char_id(char_id)
        return os.path.join(self.character_dir(ctx), f"{cid}.json")

    def relations_path(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.character_dir(ctx), "relations.json")

    def player_dir(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.game_dir_from_ctx(ctx), "player")

    def player_path(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.player_dir(ctx), "player.json")

    def saves_dir(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.game_dir_from_ctx(ctx), "saves")

    def save_path(self, ctx: Optional[GameContext], slot_id: str) -> str:
        sid = validate_slot_id(slot_id)
        return os.path.join(self.saves_dir(ctx), f"save_{sid}.json")

    def history_path(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.saves_dir(ctx), "history.json")

    def snapshots_dir(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.game_dir_from_ctx(ctx), "snapshots")

    def snapshot_path(self, ctx: Optional[GameContext], chapter: int) -> str:
        return os.path.join(self.snapshots_dir(ctx), f"chapter_{chapter:03d}.json")



    def novel_dir(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.game_dir_from_ctx(ctx), "novel")

    def current_novel_dir(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.novel_dir(ctx), "current")

    def current_novel_chapters_dir(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.current_novel_dir(ctx), "chapters")

    def novel_state_path(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.current_novel_dir(ctx), "novel_state.json")

    def current_plan_path(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.current_novel_dir(ctx), "plan.json")

    def current_merged_novel_path(self, ctx: Optional[GameContext]) -> str:
        return os.path.join(self.current_novel_dir(ctx), "novel.md")

    def legacy_novel_dir(self, ctx: Optional[GameContext], folder: str) -> str:
        safe_folder = validate_novel_folder(folder)
        return os.path.join(self.novel_dir(ctx), safe_folder)

    def llm_log_path(self, ctx: Optional[GameContext]) -> Optional[str]:
        if ctx is None:
            return None
        return os.path.join(self.game_dir_from_ctx(ctx), "llm-log.md")
