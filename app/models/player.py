from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.scenarios import DEFAULT_SCENARIO_TYPE, normalize_scenario_type


class InventoryItem(BaseModel):
    id: str = ""
    name: str
    type: str = "misc"
    qty: int = 1
    effects: List[str] = []
    description: str = ""


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
    title: str = ""
    background: str = ""
    appearance: str = ""
    personality: str = ""
    scenario_type: str = DEFAULT_SCENARIO_TYPE

    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    max_hp: int = 10
    current_hp: int = 10

    skills: List[PlayerSkill] = []
    skill_exp: Dict[str, int] = {}
    growth_log: List[str] = []
    inventory: List[Any] = []

    created_at: str = ""
    updated_at: str = ""

    def calculate_modifier(self, attribute: str) -> int:
        value = getattr(self, attribute, 10)
        return (value - 10) // 2


class PlayerUpdateRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    title: Optional[str] = None
    background: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    scenario_type: Optional[str] = None
    strength: Optional[int] = None
    dexterity: Optional[int] = None
    constitution: Optional[int] = None
    intelligence: Optional[int] = None
    wisdom: Optional[int] = None
    charisma: Optional[int] = None
    skills: Optional[List[Dict]] = None


class PlayerCreateRequest(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    title: str = ""
    background: str = ""
    appearance: str = ""
    personality: str = ""
    scenario_type: str = DEFAULT_SCENARIO_TYPE
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
    scenario_type: str = DEFAULT_SCENARIO_TYPE


SCENARIO_PRESET_SKILLS: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "jianghu": {
        "combat": [
            {"name": "剑术", "description": "讲究步伐、角度与出手时机的兵刃功夫", "related_attribute": "strength"},
            {"name": "刀法", "description": "以狠、快、压迫感见长的近身交锋技巧", "related_attribute": "strength"},
            {"name": "轻功", "description": "翻墙越脊、腾挪闪避与提气纵跃", "related_attribute": "dexterity"},
            {"name": "拳掌", "description": "徒手近战与拆招发力的实战功夫", "related_attribute": "strength"},
            {"name": "暗器", "description": "短距偷袭、藏器出手与角度判断", "related_attribute": "dexterity"},
            {"name": "内功", "description": "调息运劲、耐力恢复与伤势承压能力", "related_attribute": "constitution"},
        ],
        "social": [
            {"name": "察言观色", "description": "从礼数、口风与神情里判断真意", "related_attribute": "wisdom"},
            {"name": "江湖话术", "description": "在人情与规矩之间试探、套话与斡旋", "related_attribute": "charisma"},
            {"name": "威逼", "description": "借名声、气势或兵刃压迫对手松口", "related_attribute": "charisma"},
        ],
        "knowledge": [
            {"name": "医术", "description": "处理创伤、辨症与配置常用药方", "related_attribute": "intelligence"},
            {"name": "毒理", "description": "识毒、解毒与判断下毒痕迹", "related_attribute": "intelligence"},
            {"name": "机关", "description": "看破暗门、陷阱与匣盒构造", "related_attribute": "intelligence"},
            {"name": "江湖阅历", "description": "熟悉门派、地盘、黑话与旧案传闻", "related_attribute": "intelligence"},
            {"name": "术数", "description": "识符、看局与理解民间秘术传闻", "related_attribute": "wisdom"},
        ],
        "survival": [
            {"name": "潜行", "description": "隐蔽接近、借地形藏身与脱身", "related_attribute": "dexterity"},
            {"name": "追踪", "description": "循脚印、气味与江湖痕迹找人", "related_attribute": "wisdom"},
            {"name": "野路求生", "description": "在荒郊野岭过夜、找水与辨路", "related_attribute": "constitution"},
        ],
    },
    "grim_fantasy": {
        "combat": [
            {"name": "剑斗", "description": "实用而残酷的近战剑技，强调体力与破绽", "related_attribute": "strength"},
            {"name": "长枪", "description": "在阵线、巷战或守御中控制距离", "related_attribute": "strength"},
            {"name": "骑术", "description": "驭马、冲锋与长途行军中的控骑能力", "related_attribute": "dexterity"},
            {"name": "盾卫", "description": "以防具、站位与耐力顶住正面压力", "related_attribute": "constitution"},
        ],
        "social": [
            {"name": "宫廷礼法", "description": "理解头衔、席位与言语中的等级边界", "related_attribute": "charisma"},
            {"name": "谍报", "description": "打探消息、经营耳目与甄别真假情报", "related_attribute": "wisdom"},
            {"name": "审讯", "description": "通过压力、沉默与细节拆穿说辞", "related_attribute": "charisma"},
            {"name": "经商", "description": "议价、算账与在短缺中换取所需物资", "related_attribute": "charisma"},
        ],
        "knowledge": [
            {"name": "纹章学", "description": "辨认家徽、谱系与旧誓约的象征", "related_attribute": "intelligence"},
            {"name": "古老传说", "description": "掌握旧王朝、异象与边境怪谈的线索", "related_attribute": "intelligence"},
            {"name": "禁忌学识", "description": "理解危险仪式、预兆与被压抑的秘密知识", "related_attribute": "intelligence"},
        ],
        "survival": [
            {"name": "潜行", "description": "在林地、废墟与堡垒阴影中藏身潜入", "related_attribute": "dexterity"},
            {"name": "求生", "description": "面对严寒、饥饿与长途跋涉时维持生机", "related_attribute": "constitution"},
            {"name": "医治", "description": "处理伤口、感染与战后虚弱", "related_attribute": "wisdom"},
            {"name": "侦察", "description": "观察地形、踪迹与潜伏威胁", "related_attribute": "wisdom"},
        ],
    },
}

PRESET_SKILLS: Dict[str, List[Dict[str, str]]] = SCENARIO_PRESET_SKILLS[DEFAULT_SCENARIO_TYPE]


def get_preset_skills_for_scenario(scenario_type: Optional[str]) -> Dict[str, List[Dict[str, str]]]:
    key = normalize_scenario_type(scenario_type)
    return SCENARIO_PRESET_SKILLS.get(key, SCENARIO_PRESET_SKILLS[DEFAULT_SCENARIO_TYPE])


LEGACY_SKILL_INDEX: Dict[str, Dict[str, str]] = {
    skill["name"]: {
        "category": category,
        "description": skill["description"],
        "related_attribute": skill["related_attribute"],
    }
    for scenario_skills in SCENARIO_PRESET_SKILLS.values()
    for category, skills in scenario_skills.items()
    for skill in skills
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
