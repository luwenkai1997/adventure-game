from typing import Optional

from app.game_context import GameContext
from app.repositories.base import FileRepositoryPaths
from app.utils.atomic_io import atomic_append_text


class LLMLogRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def path_for(self, ctx: Optional[GameContext]) -> Optional[str]:
        return self.paths.llm_log_path(ctx)

    def append(self, ctx: Optional[GameContext], body: str) -> None:
        path = self.path_for(ctx)
        if not path:
            return
        atomic_append_text(path, body)
