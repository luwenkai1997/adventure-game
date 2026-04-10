import json
import os
from typing import Dict, Optional

from app.repositories.base import FileRepositoryPaths
from app.utils.atomic_io import atomic_write_json


class SessionRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths
        self._session_game_map: Optional[Dict[str, Optional[str]]] = None

    def _load(self) -> Dict[str, Optional[str]]:
        if self._session_game_map is not None:
            return self._session_game_map

        session_map: Dict[str, Optional[str]] = {}
        path = self.paths.session_store_path()
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(key, str) and (
                            value is None or isinstance(value, str)
                        ):
                            session_map[key] = value
        except Exception:
            session_map = {}

        self._session_game_map = session_map
        return session_map

    def _persist(self) -> None:
        atomic_write_json(self.paths.session_store_path(), self._load())

    def _session_key(self, session_id: Optional[str]) -> str:
        return session_id or "default"

    def get_active_game_id(self, session_id: Optional[str]) -> Optional[str]:
        return self._load().get(self._session_key(session_id))

    def set_active_game(self, session_id: Optional[str], game_id: str) -> None:
        self._load()[self._session_key(session_id)] = game_id
        self._persist()

    def clear_game(self, session_id: Optional[str]) -> None:
        data = self._load()
        key = self._session_key(session_id)
        if key in data:
            del data[key]
            self._persist()

    def remove_game_references(self, game_id: str) -> None:
        data = self._load()
        stale_keys = [key for key, value in data.items() if value == game_id]
        if not stale_keys:
            return
        for key in stale_keys:
            del data[key]
        self._persist()

    def resolve_active_game(
        self, session_id: Optional[str], game_repository
    ) -> Optional[str]:
        data = self._load()
        candidate_keys = []
        session_key = self._session_key(session_id)
        if session_key in data:
            candidate_keys.append(session_key)
        if "default" in data and "default" not in candidate_keys:
            candidate_keys.append("default")

        for key in candidate_keys:
            game_id = data.get(key)
            if game_id and game_repository.exists(game_id):
                return game_id
            if key in data:
                del data[key]
                self._persist()

        return game_repository.get_latest_game_id()
