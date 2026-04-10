import json
import os
from typing import Any, Dict, List, Optional

from app.game_context import GameContext
from app.repositories.base import FileRepositoryPaths
from app.utils.atomic_io import atomic_write_json, atomic_write_text


class NovelRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def ensure_current(self, ctx: GameContext) -> str:
        current_dir = self.paths.current_novel_dir(ctx)
        chapters_dir = self.paths.current_novel_chapters_dir(ctx)
        os.makedirs(current_dir, exist_ok=True)
        os.makedirs(chapters_dir, exist_ok=True)
        return current_dir

    def load_current_state(self, ctx: Optional[GameContext]) -> Optional[Dict[str, Any]]:
        if ctx is None:
            return None
        path = self.paths.novel_state_path(ctx)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def save_current_state(self, ctx: GameContext, state: Dict[str, Any]) -> None:
        self.ensure_current(ctx)
        atomic_write_json(self.paths.novel_state_path(ctx), state)

    def save_current_plan(self, ctx: GameContext, plan: Dict[str, Any]) -> str:
        self.ensure_current(ctx)
        path = self.paths.current_plan_path(ctx)
        atomic_write_json(path, plan)
        return path

    def load_text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def save_current_chapter(self, ctx: GameContext, filename: str, content: str) -> str:
        self.ensure_current(ctx)
        path = os.path.join(self.paths.current_novel_chapters_dir(ctx), filename)
        atomic_write_text(path, content)
        return path

    def list_current_chapter_files(self, ctx: GameContext) -> List[str]:
        chapters_dir = self.paths.current_novel_chapters_dir(ctx)
        if not os.path.exists(chapters_dir):
            return []
        return sorted(name for name in os.listdir(chapters_dir) if name.endswith(".md"))

    def save_current_merged_novel(self, ctx: GameContext, content: str) -> str:
        self.ensure_current(ctx)
        path = self.paths.current_merged_novel_path(ctx)
        atomic_write_text(path, content)
        return path

    def load_current_merged_novel(self, ctx: Optional[GameContext]) -> Optional[str]:
        if ctx is None:
            return None
        path = self.paths.current_merged_novel_path(ctx)
        if os.path.exists(path):
            return self.load_text(path)
        return None

    def ensure_legacy_folder(self, ctx: GameContext, folder: str) -> str:
        path = self.paths.legacy_novel_dir(ctx, folder)
        os.makedirs(path, exist_ok=True)
        return path

    def legacy_plan_path(self, ctx: GameContext, folder: str) -> str:
        return os.path.join(self.ensure_legacy_folder(ctx, folder), "plan.json")

    def legacy_chapters_dir(self, ctx: GameContext, folder: str) -> str:
        path = os.path.join(self.ensure_legacy_folder(ctx, folder), "chapters")
        os.makedirs(path, exist_ok=True)
        return path

    def legacy_novel_path(self, ctx: GameContext, folder: str) -> str:
        return os.path.join(self.ensure_legacy_folder(ctx, folder), "novel.md")

    def save_legacy_plan(self, ctx: GameContext, folder: str, plan: Dict[str, Any]) -> str:
        path = self.legacy_plan_path(ctx, folder)
        atomic_write_json(path, plan)
        return path

    def load_legacy_plan(self, ctx: GameContext, folder: str) -> Dict[str, Any]:
        path = self.legacy_plan_path(ctx, folder)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_legacy_chapter(
        self, ctx: GameContext, folder: str, filename: str, content: str
    ) -> str:
        path = os.path.join(self.legacy_chapters_dir(ctx, folder), filename)
        atomic_write_text(path, content)
        return path

    def list_legacy_chapter_files(self, ctx: GameContext, folder: str) -> List[str]:
        chapters_dir = self.legacy_chapters_dir(ctx, folder)
        return sorted(name for name in os.listdir(chapters_dir) if name.endswith(".md"))

    def save_legacy_merged_novel(
        self, ctx: GameContext, folder: str, content: str
    ) -> str:
        path = self.legacy_novel_path(ctx, folder)
        atomic_write_text(path, content)
        return path
