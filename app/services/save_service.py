from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.save import SaveCreateRequest
from app.config import MAX_SAVE_SLOTS, MAX_HISTORY_STEPS
from app.utils.file_storage import (
    list_saves,
    save_game_state,
    load_game_state,
    delete_game_save,
    save_history,
    load_history,
)


class SaveService:
    def __init__(self):
        pass

    def list_saves(self) -> List[Dict[str, Any]]:
        saves = list_saves()

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

    def get_save(self, slot_id: str) -> Optional[Dict[str, Any]]:
        return load_game_state(slot_id)

    def save_game(self, request: SaveCreateRequest) -> Dict[str, Any]:
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
        }

        filepath = save_game_state(request.slot_id, save_data)
        return {"success": True, "filepath": filepath, "save": save_data}

    def delete_save(self, slot_id: str) -> bool:
        return delete_game_save(slot_id)

    def load_save(self, slot_id: str) -> Optional[Dict[str, Any]]:
        return self.get_save(slot_id)

    def push_history(self, snapshot: Dict[str, Any]) -> None:
        history = load_history()

        snapshot["step"] = len(history) + 1
        snapshot["timestamp"] = datetime.now().isoformat()

        history.append(snapshot)

        if len(history) > MAX_HISTORY_STEPS:
            history = history[-MAX_HISTORY_STEPS:]

        save_history(history)

    def undo(self) -> Optional[Dict[str, Any]]:
        history = load_history()

        if not history:
            return None

        last_snapshot = history.pop()
        save_history(history)

        return last_snapshot

    def get_history(self) -> List[Dict[str, Any]]:
        history = load_history()

        return [
            {
                "step": i + 1,
                "timestamp": h.get("timestamp", ""),
                "chapter": h.get("chapter", 0),
                "preview_scene": h.get("preview_scene", "")[:100] + "...",
            }
            for i, h in enumerate(history)
        ]

    def clear_history(self) -> None:
        save_history([])

    def get_history_count(self) -> int:
        return len(load_history())
