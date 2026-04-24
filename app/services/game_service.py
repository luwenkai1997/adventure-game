import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.config import MEMORY_UPDATE_PROMPT
from app.game_context import GameContext
from app.models.chat import ChatTurnContent
from app.services.prompt_composer import PromptComposer
from app.utils.memory_utils import ensure_story_flow_round_present


def _format_optional_section(value: Any, fallback: str = "无") -> str:
    """Render optional structured fields (list/dict) for inclusion inside the prompt."""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value if value.strip() else fallback
    if isinstance(value, (list, dict)):
        if not value:
            return fallback
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


class GameService:
    def __init__(
        self,
        prompt_composer: PromptComposer,
        memory_repository,
        save_repository,
        character_repository,
        relation_repository,
        llm_adapter,
    ):
        self.composer = prompt_composer
        self.memory_repository = memory_repository
        self.save_repository = save_repository
        self.character_repository = character_repository
        self.relation_repository = relation_repository
        self.llm_adapter = llm_adapter

    async def update_memory(
        self,
        ctx: GameContext,
        scene: str,
        selected_choice: str,
        log_summary: str,
        ending_type: str = "",
        check_result: Optional[Any] = None,
        relationship_changes: Optional[Any] = None,
        route_scores: Optional[Any] = None,
        current_round: Optional[int] = None,
    ) -> str:
        memory_content = self.memory_repository.load_text(ctx)

        if current_round is None or current_round <= 0:
            current_round = max(1, self.save_repository.get_round_count(ctx))

        prompt = MEMORY_UPDATE_PROMPT.format(
            memory_content=memory_content,
            scene=scene,
            selected_choice=selected_choice,
            log_summary=log_summary,
            ending_type=ending_type or "无",
            check_result=_format_optional_section(check_result),
            relationship_changes=_format_optional_section(relationship_changes),
            route_scores=_format_optional_section(route_scores),
            current_round=current_round,
        )

        new_memory = await self.llm_adapter.generate_text(
            ctx=ctx,
            prompt=prompt,
            method_name="update_memory",
            use_utility_model=True,
        )
        new_memory = ensure_story_flow_round_present(
            new_memory, current_round, scene, selected_choice, log_summary
        )
        self.memory_repository.save_text(ctx, new_memory)
        return new_memory

    async def chat(
        self,
        ctx: Optional[GameContext],
        messages: List[Dict],
        extra_prompt: str = "",
        turn_context: Optional[Dict] = None,
    ) -> Tuple[ChatTurnContent, str, bool]:
        tendency_data = None
        if turn_context:
            tendency_data = turn_context.get("tendency")
        full_messages = self.composer.compose(
            ctx=ctx,
            messages=messages,
            extra_prompt=extra_prompt,
            turn_context=turn_context,
            tendency_data=tendency_data,
        )
        return await self.llm_adapter.generate_chat_turn(ctx, full_messages)

    async def apply_relationship_changes(
        self, ctx: Optional[GameContext], relationship_changes
    ) -> None:
        if ctx is None or not relationship_changes:
            return

        relations = self.relation_repository.load_all(ctx)
        characters = self.character_repository.load_all(ctx)
        characters_by_name = {char.get("name"): char for char in characters}

        for change in relationship_changes:
            target_char = characters_by_name.get(change.character_name)
            if not target_char:
                continue

            char_id = target_char.get("id")
            for relation in relations:
                if relation.get("source_id") == char_id or relation.get("target_id") == char_id:
                    old_strength = relation.get("strength", 50)
                    delta = change.value if change.change_type == "+" else -change.value
                    new_strength = max(0, min(100, old_strength + delta))
                    relation["strength"] = new_strength

                    old_type = relation.get("type", "neutral")
                    new_type = old_type

                    if new_strength >= 80:
                        if old_type in ["enemy", "neutral", "rival"]:
                            new_type = "friend"
                    elif new_strength <= 20:
                        if old_type not in ["enemy"]:
                            new_type = "enemy"
                    elif 20 < new_strength < 80:
                        if old_type == "enemy" and new_strength >= 40:
                            new_type = "neutral"
                        elif old_type in ["friend", "lover", "ally"] and new_strength <= 50:
                            new_type = "neutral"

                    if new_type != old_type:
                        relation["type"] = new_type
                        relation.setdefault("events", []).append(
                            {
                                "type": "立场转变",
                                "value": 0,
                                "reason": f"关系发生质变，从[{old_type}]转变为[{new_type}]",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                    relation.setdefault("events", []).append(
                        {
                            "type": change.change_type,
                            "value": change.value,
                            "reason": change.reason or "",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

        self.relation_repository.save_all(ctx, relations)

    def apply_inventory_changes(
        self, ctx: Optional[GameContext], inventory_changes
    ) -> None:
        """Apply add/remove/update operations to the player's inventory."""
        if ctx is None or not inventory_changes:
            return

        player_data = self.player_repository.load(ctx)
        if not player_data:
            return

        import uuid as _uuid

        raw_inventory = player_data.get("inventory", [])
        items: List[Dict] = []
        for entry in raw_inventory:
            if isinstance(entry, str):
                items.append({"id": _uuid.uuid4().hex[:8], "name": entry, "type": "misc", "qty": 1, "effects": []})
            elif isinstance(entry, dict):
                items.append(entry)

        for change in inventory_changes:
            op = change.op if hasattr(change, "op") else change.get("op", "add")
            name = change.item_name if hasattr(change, "item_name") else change.get("item_name", "")
            qty = change.qty if hasattr(change, "qty") else change.get("qty", 1)

            if op == "add":
                existing = next((i for i in items if i["name"] == name), None)
                if existing:
                    existing["qty"] = existing.get("qty", 1) + qty
                else:
                    items.append({
                        "id": _uuid.uuid4().hex[:8],
                        "name": name,
                        "type": change.item_type if hasattr(change, "item_type") else change.get("item_type", "misc"),
                        "qty": qty,
                        "effects": change.effects if hasattr(change, "effects") else change.get("effects") or [],
                        "description": change.description if hasattr(change, "description") else change.get("description", ""),
                    })
            elif op == "remove":
                for item in items:
                    if item["name"] == name:
                        item["qty"] = max(0, item.get("qty", 1) - qty)
                items = [i for i in items if i.get("qty", 1) > 0]
            elif op == "update":
                for item in items:
                    if item["name"] == name:
                        if hasattr(change, "effects") and change.effects is not None:
                            item["effects"] = change.effects
                        if hasattr(change, "description") and change.description:
                            item["description"] = change.description

        player_data["inventory"] = items
        self.player_repository.save(ctx, player_data)
