"""
Runtime configuration loaded from environment variables.

All LLM prompt templates live in app/prompts/__init__.py.
"""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_SAVE_SLOTS = 5
MAX_HISTORY_STEPS = 10

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.getenv("API_KEY", "")
API_MODEL = os.getenv("API_MODEL", "gpt-4o-mini")
API_MODEL_UTILITY = os.getenv("API_MODEL_UTILITY", API_MODEL)  # cheaper model for utility calls
API_IMAGE_MODEL = os.getenv("API_IMAGE_MODEL", "dall-e-3")
API_IMAGE_ENABLED = os.getenv("API_IMAGE_ENABLED", "false").lower() == "true"
API_STREAMING_ENABLED = os.getenv("API_STREAMING_ENABLED", "true").lower() == "true"
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "120"))

# Re-export all prompt constants so existing `from app.config import X` imports keep working.
from app.prompts import (  # noqa: E402, F401
    ACTION_ADVENTURE_GUIDELINES,
    CHARACTER_DETAIL_GENERATION_PROMPT,
    CHARACTER_LIST_GENERATION_PROMPT,
    JSON_OUTPUT_RULES,
    MEMORY_UPDATE_PROMPT,
    NOVEL_CHAPTER_PROMPT,
    NOVEL_ENDING_PROMPT,
    NOVEL_FIDELITY_RULES,
    NOVEL_GENERATION_PROMPT,
    NOVEL_INCREMENTAL_PLAN_PROMPT,
    NOVEL_TITLE_PROMPT,
    NPC_DETAIL_GENERATION_PROMPT,
    NPC_DIALOGUE_PROMPT,
    NPC_LIST_GENERATION_PROMPT,
    PLAYER_GENERATION_PROMPT,
    RELATION_GENERATION_PROMPT,
    RELATION_TYPES,
    ROLE_DESCRIPTIONS,
    ROLE_IMPORTANCE,
    ROLE_TYPE_CN,
    ROUTE_TENDENCY_MAPPING,
    STORY_EXPANSION_PROMPT,
    SYSTEM_PROMPT,
    UNIVERSAL_PROMPT,
    UNIVERSAL_PROMPT_LITE,
)
