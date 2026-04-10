from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.config import MEMORY_UPDATE_PROMPT
from app.game_context import GameContext
from app.models.chat import ChatTurnContent
from app.services.prompt_composer import PromptComposer


class GameService:
    def __init__(
        self,
        prompt_composer: PromptComposer,
        memory_repository,
        character_repository,
        relation_repository,
        llm_adapter,
    ):
        self.composer = prompt_composer
        self.memory_repository = memory_repository
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
    ) -> str:
        memory_content = self.memory_repository.load_text(ctx)

        prompt = MEMORY_UPDATE_PROMPT.format(
            memory_content=memory_content,
            scene=scene,
            selected_choice=selected_choice,
            log_summary=log_summary,
            ending_type=ending_type or "无",
        )

        new_memory = await self.llm_adapter.generate_text(
            ctx=ctx,
            prompt=prompt,
            method_name="update_memory",
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
                    relation["strength"] = max(0, min(100, old_strength + delta))
                    relation.setdefault("events", []).append(
                        {
                            "type": change.change_type,
                            "value": change.value,
                            "reason": change.reason or "",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

        self.relation_repository.save_all(ctx, relations)
