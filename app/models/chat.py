from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class CheckSpec(BaseModel):
    attribute: str = "strength"
    skill: Optional[str] = None
    difficulty: int = 12
    description: Optional[str] = None


class RelationshipChange(BaseModel):
    character_name: str
    change_type: str = "+"
    value: int = 0
    reason: Optional[str] = None


class ChoiceItem(BaseModel):
    text: str
    check: Optional[CheckSpec] = None
    check_optional: bool = True
    check_prompt: Optional[str] = None
    tendency: Optional[List[str]] = None
    is_key_decision: bool = False
    consequence_hint: Optional[str] = None


class ChatTurnContent(BaseModel):
    scene: str
    log: str
    choices: Optional[List[ChoiceItem]] = None
    ending: Optional[str] = None
    relationship_changes: Optional[List[RelationshipChange]] = None


class ChatRequestV2(BaseModel):
    messages: List[Dict]
    extraPrompt: str = ""
    turn_context: Optional[Dict] = None


class ChatResponseV2(BaseModel):
    success: bool
    content: ChatTurnContent
    raw_content: Optional[str] = None
    meta: Dict = Field(default_factory=dict)


class NPCDialogueRequest(BaseModel):
    message: str
    context: Optional[str] = None


class NPCDialogueResponse(BaseModel):
    dialogue: str
    mood: Optional[str] = None
    relationship_hint: Optional[str] = None
