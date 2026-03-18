from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class SkillModel(BaseModel):
    id: str = ""
    name: str
    category: str = "general"
    level: int = 1
    max_level: int = 10
    description: str = ""
    effects: List[str] = []
    cooldown: int = 0
    mana_cost: int = 0


class AppearanceModel(BaseModel):
    height: str = ""
    build: str = ""
    hair_color: str = ""
    eye_color: str = ""
    distinguishing_features: str = ""
    clothing_style: str = ""
    avatar_prompt: str = ""
    full_description: str = ""


class BackgroundModel(BaseModel):
    origin: str = ""
    occupation: str = ""
    affiliation: str = ""
    backstory: str = ""
    motivations: str = ""
    secrets: str = ""
    goals: str = ""


class PersonalityModel(BaseModel):
    traits: List[str] = []
    mbti: str = ""
    alignment: str = ""
    values: List[str] = []
    fears: List[str] = []
    likes: List[str] = []
    dislikes: List[str] = []
    dialogue_style: str = ""


class AttributesModel(BaseModel):
    health: int = 100
    max_health: int = 100
    mana: int = 100
    max_mana: int = 100
    strength: int = 10
    agility: int = 10
    intelligence: int = 10
    charisma: int = 10
    luck: int = 10
    reputation: int = 50
    wealth: int = 50
    influence: int = 50


class StatusModel(BaseModel):
    current_state: str = "active"
    location: str = ""
    conditions: List[str] = []
    mood: str = "neutral"
    last_activity: str = ""
    story_progress: Dict = {}


class CharacterCard(BaseModel):
    id: str = ""
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    role_type: str = "npc"
    importance: int = 1
    first_appearance: int = 0
    title: str = ""
    description: str = ""
    appearance: AppearanceModel = AppearanceModel()
    background: BackgroundModel = BackgroundModel()
    personality: PersonalityModel = PersonalityModel()
    attributes: AttributesModel = AttributesModel()
    skills: List[SkillModel] = []
    status: StatusModel = StatusModel()
    relationships: List[str] = []
    tags: List[str] = []
    created_at: str = ""
    updated_at: str = ""
    generated_by: str = "auto"


class CharacterCreate(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    role_type: str = "npc"
    importance: int = 1
    title: str = ""
    description: str = ""
    appearance: Optional[AppearanceModel] = None
    background: Optional[BackgroundModel] = None
    personality: Optional[PersonalityModel] = None
    attributes: Optional[AttributesModel] = None
    skills: List[SkillModel] = []
    tags: List[str] = []
    status: Optional[StatusModel] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    role_type: Optional[str] = None
    importance: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[AppearanceModel] = None
    background: Optional[BackgroundModel] = None
    personality: Optional[PersonalityModel] = None
    attributes: Optional[AttributesModel] = None
    skills: Optional[List[SkillModel]] = None
    status: Optional[StatusModel] = None
    tags: Optional[List[str]] = None


class RelationEvent(BaseModel):
    chapter: int
    event_type: str = "established"
    event: str
    strength_change: int = 0
    trust_change: int = 0


class CharacterRelation(BaseModel):
    id: str = ""
    source_id: str
    target_id: str
    relation_type: str = "neutral"
    strength: int = 50
    trust: int = 50
    description: str = ""
    since_chapter: int = 1
    events: List[RelationEvent] = []
    is_public: bool = True


class RelationCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str = "neutral"
    strength: int = 50
    trust: int = 50
    description: str = ""
    since_chapter: int = 1
    is_public: bool = True


class RelationUpdate(BaseModel):
    relation_type: Optional[str] = None
    strength: Optional[int] = None
    trust: Optional[int] = None
    description: Optional[str] = None
    events: Optional[List[RelationEvent]] = None
    is_public: Optional[bool] = None


class CharacterGenerationConfig(BaseModel):
    world_setting: str
    genre: str = "fantasy"
    tone: str = "serious"
    total_characters: int = 20
    protagonist_count: int = 1
    antagonist_count: int = 2
    supporting_count: int = 7
    npc_count: int = 10
    power_level: str = "medium"
    complexity: str = "medium"
    include_romance: bool = True
    include_faction: bool = True


class GenerateCharactersRequest(BaseModel):
    world_setting: str
    config: Optional[CharacterGenerationConfig] = None


class StateEffect(BaseModel):
    effect_type: str
    target: str
    value: Any
    description: str = ""


class StateUpdateRequest(BaseModel):
    character_id: str
    effects: List[StateEffect] = []
    reason: str = ""


class BatchUpdateRequest(BaseModel):
    updates: List[StateUpdateRequest] = []
