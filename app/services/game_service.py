from typing import List, Dict
import requests
from app.config import (
    API_BASE_URL,
    API_MODEL,
    API_KEY,
    SYSTEM_PROMPT,
    MEMORY_UPDATE_PROMPT,
)
from app.utils.file_storage import (
    load_memory,
    save_memory_text,
)


class GameService:
    def __init__(self):
        pass

    def update_memory(self, scene: str, selected_choice: str, log_summary: str, ending_type: str = "") -> str:
        memory_content = load_memory()

        prompt = MEMORY_UPDATE_PROMPT.format(
            memory_content=memory_content,
            scene=scene,
            selected_choice=selected_choice,
            log_summary=log_summary,
            ending_type=ending_type or "无"
        )

        from app.utils.llm_client import call_llm
        new_memory = call_llm(prompt)
        save_memory_text(new_memory)
        return new_memory

    def chat(self, messages: List[Dict], extra_prompt: str = "") -> str:
        system_prompt = SYSTEM_PROMPT
        if extra_prompt:
            system_prompt = SYSTEM_PROMPT + "\n\n" + extra_prompt

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }

        payload = {
            'model': API_MODEL,
            'messages': full_messages
        }

        response = requests.post(
            f'{API_BASE_URL}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code}")

        result = response.json()
        return result['choices'][0]['message']['content']
