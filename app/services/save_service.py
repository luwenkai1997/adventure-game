from typing import List, Optional, Dict, Any
from datetime import datetime
from app.game_context import GameContext
from app.models.save import SaveCreateRequest
from app.config import MAX_SAVE_SLOTS, MAX_HISTORY_STEPS


class SaveService:
    def __init__(self, save_repository):
        self.save_repository = save_repository

    def list_saves(self, ctx: GameContext) -> List[Dict[str, Any]]:
        saves = self.save_repository.list_saves(ctx)

        save_list = []
        for slot_id in range(1, MAX_SAVE_SLOTS + 1):
            slot_str = str(slot_id)
            save_data = next((s for s in saves if s.get("slot_id") == slot_str), None)

            if save_data:
                save_list.append(
                    {
                        "slot_id": slot_str,
                        "save_name": save_data.get("save_name", f"存档 {slot_id}"),
                        "timestamp": save_data.get("timestamp", ""),
                        "world_setting": save_data.get("world_setting", ""),
                        "chapter": save_data.get("chapter", 0),
                        "preview_scene": save_data.get("preview_scene", ""),
                        "has_save": True,
                    }
                )
            else:
                save_list.append(
                    {
                        "slot_id": slot_str,
                        "save_name": f"存档 {slot_id}",
                        "timestamp": "",
                        "world_setting": "",
                        "chapter": 0,
                        "preview_scene": "",
                        "has_save": False,
                    }
                )

        return save_list

    def get_save(self, ctx: Optional[GameContext], slot_id: str) -> Optional[Dict[str, Any]]:
        return self.save_repository.load_game_state(ctx, slot_id)

    def save_game(self, ctx: GameContext, request: SaveCreateRequest) -> Dict[str, Any]:
        save_data = {
            "slot_id": request.slot_id,
            "save_name": request.save_name,
            "timestamp": datetime.now().isoformat(),
            "world_setting": request.world_setting,
            "chapter": request.chapter,
            "messages": request.messages,
            "logs": request.logs,
            "current_scene": request.current_scene,
            "current_choices": request.current_choices,
            "player": request.player,
            "characters": request.characters,
            "relations": request.relations,
            "ending_triggered": request.ending_triggered,
            "ending_countdown": request.ending_countdown,
            "selected_ending_type": request.selected_ending_type,
            "preview_scene": request.preview_scene,
            "route_scores": request.route_scores if request.route_scores else {},
            "key_decisions": request.key_decisions if request.key_decisions else [],
            "ending_omen_state": request.ending_omen_state if request.ending_omen_state else {},
            "history": self.save_repository.load_history(ctx),
        }

        filepath = self.save_repository.save_game_state(ctx, request.slot_id, save_data)
        return {"success": True, "filepath": filepath, "save": save_data}

    def restore_history(self, ctx: GameContext, history: list) -> None:
        self.save_repository.save_history(ctx, history)

    def delete_save(self, ctx: GameContext, slot_id: str) -> bool:
        return self.save_repository.delete_game_state(ctx, slot_id)

    def load_save(self, ctx: Optional[GameContext], slot_id: str) -> Optional[Dict[str, Any]]:
        return self.get_save(ctx, slot_id)

    def push_history(self, ctx: GameContext, snapshot: Dict[str, Any]) -> None:
        history = self.save_repository.load_history(ctx)

        snapshot["step"] = len(history) + 1
        snapshot["timestamp"] = datetime.now().isoformat()

        history.append(snapshot)

        if len(history) > MAX_HISTORY_STEPS:
            history = history[-MAX_HISTORY_STEPS:]

        self.save_repository.save_history(ctx, history)

    def undo(self, ctx: GameContext) -> Optional[Dict[str, Any]]:
        history = self.save_repository.load_history(ctx)

        if not history:
            return None

        last_snapshot = history.pop()
        self.save_repository.save_history(ctx, history)

        return last_snapshot

    def get_history(self, ctx: Optional[GameContext]) -> List[Dict[str, Any]]:
        history = self.save_repository.load_history(ctx)

        return [
            {
                "step": i + 1,
                "timestamp": h.get("timestamp", ""),
                "chapter": h.get("chapter", 0),
                "preview_scene": h.get("preview_scene", "")[:100] + "...",
            }
            for i, h in enumerate(history)
        ]

    def clear_history(self, ctx: GameContext) -> None:
        self.save_repository.save_history(ctx, [])

    def get_history_count(self, ctx: Optional[GameContext]) -> int:
        return len(self.save_repository.load_history(ctx))
