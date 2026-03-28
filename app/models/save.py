from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GameSave(BaseModel):
    slot_id: str
    save_name: str
    timestamp: str
    world_setting: str
    chapter: int
    messages: List[Dict[str, Any]] = []
    logs: List[Any] = []
    current_scene: Optional[str] = ""
    current_choices: Optional[List[Any]] = []
    player: Optional[Dict[str, Any]] = None
    characters: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    ending_triggered: bool = False
    ending_countdown: int = 0
    selected_ending_type: str = ""
    preview_scene: str = ""
    route_scores: Optional[Dict[str, int]] = Field(default_factory=dict)
    key_decisions: Optional[List[Any]] = Field(default_factory=list)
    ending_omen_state: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HistorySnapshot(BaseModel):
    step: int
    timestamp: str
    messages: List[Dict[str, Any]]
    chapter: int
    current_scene: Optional[str]
    current_choices: Optional[List[Any]] = []
    player: Optional[Dict[str, Any]] = None
    route_scores: Optional[Dict[str, int]] = Field(default_factory=dict)
    key_decisions: Optional[List[Any]] = Field(default_factory=list)
    ending_omen_state: Optional[Dict[str, Any]] = Field(default_factory=dict)


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
    current_choices: Optional[List[Any]] = []
    player: Optional[Dict[str, Any]] = None
    characters: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    ending_triggered: bool = False
    ending_countdown: int = 0
    selected_ending_type: str = ""
    preview_scene: str = ""
    route_scores: Optional[Dict[str, int]] = Field(default_factory=dict)
    key_decisions: Optional[List[Any]] = Field(default_factory=list)
    ending_omen_state: Optional[Dict[str, Any]] = Field(default_factory=dict)
