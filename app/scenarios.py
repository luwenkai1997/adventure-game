from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


ScenarioType = Literal["jianghu", "grim_fantasy"]

DEFAULT_SCENARIO_TYPE: ScenarioType = "jianghu"


@dataclass(frozen=True)
class ScenarioProfile:
    type: ScenarioType
    label: str
    subtitle: str
    world_tone: str
    prose_style: str
    supernatural_rules: str
    conflict_axes: List[str]
    character_archetypes: List[str]
    item_archetypes: List[str]
    location_pool: List[str]
    route_flavor: Dict[str, str]
    memory_sections: List[str]
    player_races: List[str]
    random_names: Dict[str, List[str]]
    random_backgrounds: List[str]
    random_appearances: Dict[str, str]
    story_focus: str
    skill_categories: Dict[str, str]


SCENARIO_PROFILES: Dict[ScenarioType, ScenarioProfile] = {
    "jianghu": ScenarioProfile(
        type="jianghu",
        label="古代东方江湖",
        subtitle="门派、朝廷、帮会与恩怨交织的低奇观武侠世界",
        world_tone="社会秩序由朝廷律法、门派规矩、帮会势力与私人恩怨共同塑造。名声、人情、师承与旧案比纯粹力量更能改变命运。",
        prose_style="文风讲究收放、气口与留白。动作场面强调见招拆招、方位、兵刃与身法；对话要有潜台词、礼数与江湖黑话；悬念来自恩怨、人情债与身份揭露。",
        supernatural_rules="允许轻超凡：内功、异术、毒理、术数、奇门机关可以出现，但必须稀缺、代价明确，不能高魔泛滥，也不能把冲突写成纯法术对轰。",
        conflict_axes=["师门与叛门", "恩义与复仇", "名声与生存", "朝廷与江湖", "帮会与地方秩序"],
        character_archetypes=["落魄弟子", "旧案见证人", "名门少主", "黑道舵主", "朝廷密探", "亦敌亦友的游侠"],
        item_archetypes=["名剑与旧刀", "秘笈残页", "信物玉佩", "药材与毒囊", "密信", "机关图纸"],
        location_pool=["客栈", "山道", "镖局", "宗门", "县城", "渡口", "荒寺", "旧宅"],
        route_flavor={
            "redemption": "以义止戈、偿还旧债、救人于局中",
            "power": "扬名立威、掌控局势、压服群雄",
            "sacrifice": "舍身护人、断臂求生、以己换局",
            "betrayal": "借刀杀人、反手背盟、利用情义取胜",
            "retreat": "藏锋避祸、抽身离场、守住最后底线",
        },
        memory_sections=["恩怨账", "势力态度", "名声变化", "师承/秘笈/信物", "未了约定与江湖传闻"],
        player_races=["人类", "边地异族", "塞外后裔"],
        random_names={
            "男": ["沈孤舟", "顾长风", "陆青川", "谢无咎", "程照夜", "韩听雨"],
            "女": ["苏听雪", "叶知秋", "沈晚晴", "顾明霜", "柳轻鸿", "秦映月"],
            "其他": ["无名客", "旧伞", "乌衣行者", "江潮", "寒灯", "青岚"],
        },
        random_backgrounds=[
            "曾是小门派弟子，因旧案失去师门庇护，如今只剩一柄旧剑和一笔人情债。",
            "出身镖局旁支，自幼在江湖规矩里长大，知道什么该问、什么不该问。",
            "原是地方医者，因救错了人而卷入帮会与官府的夹缝。",
            "少年时家门被旧仇波及，从此行走四方，追查当年留下的半枚信物。",
        ],
        random_appearances={
            "人类": "衣着朴素却利落，举止带着久走江湖的警觉。",
            "边地异族": "面容带着边地血统痕迹，衣饰里混着中原与塞外风格。",
            "塞外后裔": "披风旧而耐磨，眉眼冷峻，像总在风沙里辨路的人。",
        },
        story_focus="重点写江湖规矩、势力角力、名声代价与旧怨回潮，不要写成修仙升级。",
        skill_categories={
            "combat": "江湖交手与兵刃身法",
            "social": "人情试探与话术斡旋",
            "knowledge": "医毒术数、机关与江湖见闻",
            "survival": "追踪、潜行、藏匿与野路子求生",
        },
    ),
    "grim_fantasy": ScenarioProfile(
        type="grim_fantasy",
        label="低魔西方奇幻",
        subtitle="权力、寒冬与稀薄神秘并存的中世纪式世界",
        world_tone="社会结构以家族、领主、封臣、教会与战后废墟为核心。誓言、资源、血统与传闻比英雄主义更常左右命运。",
        prose_style="文风偏冷硬、克制、具体。动作场面强调泥泞、疲惫、伤势与装备限制；对话要有阶级差、礼法与试探；戏剧张力来自盟约、饥馑、战争余波与不体面的选择。",
        supernatural_rules="允许稀薄且危险的超自然：预兆、古老仪式、禁忌学识、神迹传闻可以出现，但必须罕见、代价高、公众半信半疑，不允许常规法师施法系统。",
        conflict_axes=["家族与封臣", "忠诚与野心", "边境生存", "教会与异端", "停战与复仇"],
        character_archetypes=["失势骑士", "私生子使者", "边境医生", "家族管家", "雇佣兵队长", "掌握秘闻的修士"],
        item_archetypes=["家徽纹章", "封蜡密信", "旧誓约", "药包与盐肉", "战场遗物", "古老圣像"],
        location_pool=["城堡", "边境堡", "酒馆", "修道院", "集市", "林地驿站", "雨夜村镇", "战后荒原"],
        route_flavor={
            "redemption": "在污泥里守住良知，为他人承担代价",
            "power": "攫取封地、军权与话语权，把混乱变成自己的秩序",
            "sacrifice": "以血亲、誓言或前途换取更大的保全",
            "betrayal": "撕毁盟约、交易秘密、在权力博弈中先下手",
            "retreat": "放弃王旗与争夺，只求活着撤出风暴中心",
        },
        memory_sections=["家族/领主/封臣关系", "资源状态", "盟约与背约风险", "伤病与补给", "谣言、预兆与政治风向"],
        player_races=["人类", "边境混血", "古血后裔"],
        random_names={
            "男": ["Edric Vale", "Rowan Ash", "Gareth Thorne", "Alaric Fen", "Tomas Vane", "Corin Hale"],
            "女": ["Mira Voss", "Elena Thorne", "Ysabel Reed", "Brienne Vale", "Agnes Crow", "Lysa Fen"],
            "其他": ["Ash", "Cinder Vale", "Rook", "Morrow", "Winter Reed", "Grey Vane"],
        },
        random_backgrounds=[
            "曾在一位小领主麾下服役，见过饥荒和围城，也学会了在誓言与活命之间做选择。",
            "出身没落家族旁支，懂一点礼法、账本与刀剑，始终想夺回被人夺走的名字。",
            "曾跟随商旅与雇佣兵在边境奔波，对城堡宴会和烂泥战场都不陌生。",
            "原为修道院抄写员，因卷入一桩异端传闻，被迫带着秘密离开庇护所。",
        ],
        random_appearances={
            "人类": "风吹日晒留下粗粝痕迹，披着实用而陈旧的衣物。",
            "边境混血": "外貌混着多地血统，口音与穿着都显出边境迁徙者的影子。",
            "古血后裔": "气质让人联想到旧王朝的残影，但更多是疲惫而非神秘。",
        },
        story_focus="重点写资源匮乏、忠诚试探、阶级与权力结构，不要写成高魔冒险团。",
        skill_categories={
            "combat": "近战、骑乘与军旅经验",
            "social": "封建礼法、交易、审讯与谈判",
            "knowledge": "纹章、历史、禁忌学识与旧传说",
            "survival": "边境求生、侦察、医疗与潜行",
        },
    ),
}


def normalize_scenario_type(value: Optional[str]) -> ScenarioType:
    if value in SCENARIO_PROFILES:
        return value  # type: ignore[return-value]
    return DEFAULT_SCENARIO_TYPE


def infer_legacy_scenario_type(world_setting: str = "") -> ScenarioType:
    text = (world_setting or "").lower()
    jianghu_markers = ["江湖", "门派", "武林", "侠", "镖局", "朝廷", "客栈", "中原"]
    grim_markers = ["castle", "kingdom", "lord", "winter", "feast", "banner", "城堡", "领主", "家族", "边境", "修道院"]
    if any(marker in text for marker in grim_markers):
        return "grim_fantasy"
    if any(marker in text for marker in jianghu_markers):
        return "jianghu"
    return DEFAULT_SCENARIO_TYPE


def get_scenario_profile(scenario_type: Optional[str]) -> ScenarioProfile:
    return SCENARIO_PROFILES[normalize_scenario_type(scenario_type)]

