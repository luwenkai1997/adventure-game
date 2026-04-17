import json
from typing import Any, Dict, List, Optional, Tuple

from app.config import MEMORY_UPDATE_PROMPT
from app.services.chat_parser import (
    ChatTurnContent,
    ParseError,
    get_repair_prompt,
    parse_chat_output,
)
from app.services.llm_gateway import call_llm
from app.services.prompt_composer import PromptComposer
from app.utils.file_storage import load_history, load_memory, save_memory_text

MAX_REPAIR_ATTEMPTS = 2


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
    def __init__(self):
        self.composer = PromptComposer()

    async def update_memory(
        self,
        scene: str,
        selected_choice: str,
        log_summary: str,
        ending_type: str = "",
        check_result: Optional[Any] = None,
        relationship_changes: Optional[Any] = None,
        route_scores: Optional[Any] = None,
        current_round: Optional[int] = None,
    ) -> str:
        memory_content = load_memory()

        if current_round is None or current_round <= 0:
            current_round = max(1, len(load_history()))

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

        new_memory = await call_llm(prompt, method_name="update_memory")
        save_memory_text(new_memory)
        return new_memory

    async def chat(
        self,
        messages: List[Dict],
        extra_prompt: str = "",
        turn_context: Optional[Dict] = None,
    ) -> Tuple[ChatTurnContent, str, bool]:
        tendency_data = None
        if turn_context:
            tendency_data = turn_context.get("tendency")
        full_messages = self.composer.compose(
            messages=messages,
            extra_prompt=extra_prompt,
            turn_context=turn_context,
            tendency_data=tendency_data,
        )

        content = await call_llm(
            "",
            system_prompt=None,
            messages=full_messages,
            method_name="game_chat",
        )

        parsed_content, repaired = await self.validate_or_repair(content)
        return parsed_content, content, repaired

    async def validate_or_repair(self, raw_content: str) -> Tuple[ChatTurnContent, bool]:
        attempts = 0
        last_error = None

        while attempts <= MAX_REPAIR_ATTEMPTS:
            try:
                content, _ = parse_chat_output(raw_content)
                return content, attempts > 0
            except ParseError as e:
                last_error = e
                attempts += 1
                if attempts > MAX_REPAIR_ATTEMPTS:
                    break

                repair_prompt = get_repair_prompt(raw_content)
                raw_content = await call_llm(repair_prompt, method_name="chat_repair")

        raise last_error

    async def parse_or_repair_stream(self, full_content: str) -> Tuple[ChatTurnContent, bool]:
        attempts = 0
        raw_content = full_content
        last_error: Optional[ParseError] = None
        while attempts <= MAX_REPAIR_ATTEMPTS:
            try:
                content, _ = parse_chat_output(raw_content)
                return content, attempts > 0
            except ParseError as e:
                last_error = e
                attempts += 1
                if attempts > MAX_REPAIR_ATTEMPTS:
                    break
                raw_content = await call_llm(
                    get_repair_prompt(raw_content), method_name="chat_repair_stream"
                )
        if last_error is not None:
            raise last_error
        raise ParseError("STREAM", "parse failed", raw_content)
