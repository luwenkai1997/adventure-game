import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.game_context import GameContext
from app.repositories.base import FileRepositoryPaths
from app.utils.atomic_io import atomic_write_json


class CharacterRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def load_all(self, ctx: Optional[GameContext]) -> List[dict]:
        if ctx is None:
            return []
        char_dir = self.paths.character_dir(ctx)
        if not os.path.exists(char_dir):
            return []
        characters = []
        for filename in os.listdir(char_dir):
            if filename.endswith(".json") and filename != "relations.json":
                with open(os.path.join(char_dir, filename), "r", encoding="utf-8") as f:
                    characters.append(json.load(f))
        return characters

    def load(self, ctx: Optional[GameContext], char_id: str) -> Optional[dict]:
        if ctx is None:
            return None
        path = self.paths.character_path(ctx, char_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def save(self, ctx: GameContext, character: dict) -> str:
        if not character.get("id"):
            character["id"] = f"char_{uuid.uuid4().hex[:8]}"
        character["updated_at"] = datetime.now().isoformat()
        if "created_at" not in character:
            character["created_at"] = character["updated_at"]
        atomic_write_json(self.paths.character_path(ctx, character["id"]), character)
        return character["id"]

    def save_batch(self, ctx: GameContext, characters: List[dict]) -> int:
        saved_count = 0
        for character in characters:
            if self.save(ctx, character):
                saved_count += 1
        return saved_count

    def delete(self, ctx: GameContext, char_id: str) -> bool:
        path = self.paths.character_path(ctx, char_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


class RelationRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def load_all(self, ctx: Optional[GameContext]) -> List[dict]:
        if ctx is None:
            return []
        path = self.paths.relations_path(ctx)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_all(self, ctx: GameContext, relations: List[dict]) -> None:
        atomic_write_json(self.paths.relations_path(ctx), relations)

    def add(self, ctx: GameContext, relation: dict) -> dict:
        relations = self.load_all(ctx)
        if not relation.get("id"):
            relation["id"] = f"rel_{uuid.uuid4().hex[:8]}"
        relation["updated_at"] = datetime.now().isoformat()
        if "created_at" not in relation:
            relation["created_at"] = relation["updated_at"]
        relations.append(relation)
        self.save_all(ctx, relations)
        return relation

    def update(self, ctx: GameContext, rel_id: str, updates: dict) -> Optional[dict]:
        relations = self.load_all(ctx)
        for index, relation in enumerate(relations):
            if relation["id"] == rel_id:
                relations[index].update(updates)
                relations[index]["updated_at"] = datetime.now().isoformat()
                self.save_all(ctx, relations)
                return relations[index]
        return None

    def delete(self, ctx: GameContext, rel_id: str) -> bool:
        relations = self.load_all(ctx)
        for index, relation in enumerate(relations):
            if relation["id"] == rel_id:
                relations.pop(index)
                self.save_all(ctx, relations)
                return True
        return False


class SnapshotRepository:
    def __init__(self, paths: FileRepositoryPaths):
        self.paths = paths

    def load(self, ctx: Optional[GameContext], chapter: int) -> Optional[dict]:
        if ctx is None:
            return None
        path = self.paths.snapshot_path(ctx, chapter)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def save(self, ctx: GameContext, chapter: int, snapshot: Dict) -> str:
        path = self.paths.snapshot_path(ctx, chapter)
        atomic_write_json(path, snapshot)
        return path
