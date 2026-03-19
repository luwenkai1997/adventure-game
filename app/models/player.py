from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class PlayerSkill(BaseModel):
    id: str = ""
    name: str
    category: str
    level: int = 1
    description: str = ""
    related_attribute: str = "strength"


class PlayerCharacter(BaseModel):
    id: str = "player"
    name: str = ""
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    background: str = ""
    appearance: str = ""

    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    max_hp: int = 10
    current_hp: int = 10

    skills: List[PlayerSkill] = []
    inventory: List[str] = []

    created_at: str = ""
    updated_at: str = ""

    def calculate_modifier(self, attribute: str) -> int:
        value = getattr(self, attribute, 10)
        return (value - 10) // 2


class PlayerCreateRequest(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    background: str = ""
    appearance: str = ""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    skills: List[str] = []


class PlayerRandomRequest(BaseModel):
    world_setting: str = ""
    gender: Optional[str] = None


PRESET_SKILLS: Dict[str, List[Dict]] = {
    "combat": [
        {
            "name": "剑术",
            "description": "精通各类剑器，战斗中造成的伤害增加",
            "related_attribute": "strength",
        },
        {
            "name": "箭术",
            "description": "远程攻击能力，可从远处精准打击敌人",
            "related_attribute": "dexterity",
        },
        {
            "name": "格斗",
            "description": "徒手战斗技巧，不依赖武器也能战斗",
            "related_attribute": "strength",
        },
        {
            "name": "双持",
            "description": "双手各持武器，大幅提升攻击速度",
            "related_attribute": "dexterity",
        },
        {
            "name": "防御",
            "description": "精通盾牌和防守姿态，减少受到的伤害",
            "related_attribute": "constitution",
        },
    ],
    "social": [
        {
            "name": "说服",
            "description": "通过言语引导他人接受你的观点",
            "related_attribute": "charisma",
        },
        {
            "name": "恐吓",
            "description": "利用威势逼迫他人屈从",
            "related_attribute": "charisma",
        },
        {
            "name": "欺骗",
            "description": "巧妙掩饰真相，让他人信以为真",
            "related_attribute": "charisma",
        },
        {
            "name": "表演",
            "description": "通过表演艺术吸引和娱乐他人",
            "related_attribute": "charisma",
        },
        {
            "name": "察言观色",
            "description": "洞察他人情绪和意图",
            "related_attribute": "wisdom",
        },
    ],
    "knowledge": [
        {
            "name": "魔法学识",
            "description": "掌握魔法理论和施法技巧",
            "related_attribute": "intelligence",
        },
        {
            "name": "历史",
            "description": "了解过去的事件和典故",
            "related_attribute": "intelligence",
        },
        {
            "name": "草药",
            "description": "辨识和使用各种草药",
            "related_attribute": "intelligence",
        },
        {
            "name": "炼金",
            "description": "制作药水和其他化学制品",
            "related_attribute": "intelligence",
        },
        {
            "name": "符文",
            "description": "理解和书写神秘符文",
            "related_attribute": "intelligence",
        },
    ],
    "survival": [
        {
            "name": "潜行",
            "description": "悄无声息地移动，不被发现",
            "related_attribute": "dexterity",
        },
        {
            "name": "追踪",
            "description": "根据痕迹追踪目标",
            "related_attribute": "wisdom",
        },
        {
            "name": "野外生存",
            "description": "在野外环境下生存的能力",
            "related_attribute": "constitution",
        },
        {
            "name": "急救",
            "description": "快速处理伤口，稳定伤者",
            "related_attribute": "wisdom",
        },
        {
            "name": "开锁",
            "description": "打开各种锁具和机关",
            "related_attribute": "dexterity",
        },
    ],
}

ATTRIBUTE_NAMES_CN = {
    "strength": "力量",
    "dexterity": "敏捷",
    "constitution": "体质",
    "intelligence": "智力",
    "wisdom": "感知",
    "charisma": "魅力",
}

ATTRIBUTE_NAMES_EN = {
    "力量": "strength",
    "敏捷": "dexterity",
    "体质": "constitution",
    "智力": "intelligence",
    "感知": "wisdom",
    "魅力": "charisma",
}
