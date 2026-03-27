from typing import List, Dict, Tuple, Optional
from app.config import (
    SYSTEM_PROMPT,
    MEMORY_UPDATE_PROMPT,
)
from app.utils.file_storage import (
    load_memory,
    save_memory_text,
)
from app.services.chat_parser import (
    parse_chat_output,
    get_repair_prompt,
    ParseError,
    ChatTurnContent,
)
from app.services.prompt_composer import PromptComposer
from app.utils.llm_client import call_llm


MAX_REPAIR_ATTEMPTS = 2


class GameService:
    def __init__(self):
        self.composer = PromptComposer()

    async def update_memory(self, scene: str, selected_choice: str, log_summary: str, ending_type: str = "") -> str:
        memory_content = load_memory()

        prompt = MEMORY_UPDATE_PROMPT.format(
            memory_content=memory_content,
            scene=scene,
            selected_choice=selected_choice,
            log_summary=log_summary,
            ending_type=ending_type or "无"
        )

        new_memory = await call_llm(prompt, method_name="update_memory")
        save_memory_text(new_memory)
        return new_memory

    async def chat(
        self,
        messages: List[Dict],
        extra_prompt: str = "",
        turn_context: Optional[Dict] = None,
    ) -> Tuple[ChatTurnContent, str]:
        full_messages = self.composer.compose(
            messages=messages,
            extra_prompt=extra_prompt,
            turn_context=turn_context,
        )

        content = await call_llm(
            "\n".join([msg["content"] for msg in full_messages]),
            system_prompt=None,
            method_name="game_chat"
        )

        parsed_content, repaired = await self.validate_or_repair(content)
        return parsed_content, content

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
