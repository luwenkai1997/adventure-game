from pydantic import BaseModel


class ChatRequest(BaseModel):
    messages: list
    extraPrompt: str = ""
    endingType: str = ""


class UpdateMemoryRequest(BaseModel):
    scene: str
    selectedChoice: str
    logSummary: str
    endingType: str = ""


class MemoryRequest(BaseModel):
    worldSetting: str
    storySummary: str = ""
