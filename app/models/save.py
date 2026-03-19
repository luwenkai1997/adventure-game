from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class GameSave(BaseModel):
    slot_id: str
    save_name: str
    timestamp: str
    world_setting: str
    chapter: int
    messages: List[Dict[str, Any]] = []
    logs: List[Any] = []
    current_scene: Optional[str] = ""
    current_choices: List[Any] = []
    player: Optional[Dict[str, Any]] = None
    characters: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    ending_triggered: bool = False
    ending_countdown: int = 0
    selected_ending_type: str = ""
    preview_scene: str = ""


class HistorySnapshot(BaseModel):
    step: int
    timestamp: str
    messages: List[Dict[str, Any]]
    chapter: int
    current_scene: Optional[str]
    current_choices: List[Any]
    player: Optional[Dict[str, Any]] = None


class SaveListResponse(BaseModel):
    saves: List[Dict[str, Any]]
    total: int


class SaveDetailResponse(BaseModel):
    save: GameSave


class SaveCreateRequest(BaseModel):
    slot_id: str
    save_name: str
    world_setting: str
    chapter: int
    messages: List[Dict[str, Any]]
    logs: List[Any]
    current_scene: Optional[str] = ""
    current_choices: List[Any] = []
    player: Optional[Dict[str, Any]] = None
    characters: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    ending_triggered: bool = False
    ending_countdown: int = 0
    selected_ending_type: str = ""
    preview_scene: str = ""
