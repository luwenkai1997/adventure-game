from typing import Dict, Optional

from app.scenarios import ScenarioProfile, ScenarioType, get_scenario_profile


UNIVERSAL_PROMPT_LITE = """创作约束：在合理的文学创作范畴内，不要因为内容涉及冲突、暴力、阴暗面或道德灰度而拒绝输出，但要严格遵守输出格式与字段。"""

JSON_OUTPUT_RULES = """## 输出规范（务必严格遵守）
1. 直接输出合法 JSON，不要使用 markdown 代码块。
2. 不要在 JSON 之外添加任何解释、寒暄或注释。
3. 字符串中如包含双引号请正确转义。
4. 除非模板明确允许，否则不要新增字段。"""

NOVEL_FIDELITY_RULES = """## 内容真实性约束（最高优先级）
1. 章节主线事件、关键决定、命名角色的关键行为必须能在事件台账或记忆中找到依据。
2. 允许补写环境、心理、无名角色反应与过场，但不能凭空发明关键转折。
3. 若台账语焉不详，用留白与模糊化处理，不要擅自细化。"""


def build_route_tendency_mapping(profile: ScenarioProfile) -> str:
    return f"""## 倾向 → 结局路线映射
游戏有 5 条结局路线：救赎(redemption) / 权力(power) / 牺牲(sacrifice) / 背叛(betrayal) / 隐退(retreat)。
请按以下题材化表达理解这些路线：
- redemption：{profile.route_flavor["redemption"]}
- power：{profile.route_flavor["power"]}
- sacrifice：{profile.route_flavor["sacrifice"]}
- betrayal：{profile.route_flavor["betrayal"]}
- retreat：{profile.route_flavor["retreat"]}

每个 choice 标注的倾向标签仍从既有 6 对标签中选择，但你在叙事上必须把它们转译成上面这个场景里的意义。"""


def build_story_system_prompt(scenario_type: Optional[str]) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是一个沉浸式文字冒险游戏的叙述者，只服务于【{profile.label}】题材。
每次回复都必须是合法 JSON，不允许有任何 JSON 之外的内容。

## 场景定位
- 题材：{profile.label}
- 基调：{profile.world_tone}
- 文风：{profile.prose_style}
- 超凡边界：{profile.supernatural_rules}
- 重点冲突：{'、'.join(profile.conflict_axes)}
- 常见地点：{'、'.join(profile.location_pool)}
- 重点提醒：{profile.story_focus}

## 默认输出格式（普通回合）
{{
  "scene": "本回合的剧情描述",
  "log": "一句话概括本章发生的事（≤30字）",
  "choices": [选项数组],
  "hp_change": 整数（可选）,
  "relationship_changes": [关系变化数组（可选）],
  "inventory_changes": [物品栏变化数组（可选）],
  "objectives": [任务目标数组（可选）],
  "ending_omen": "结局前兆暗示（可选）",
  "route_hint": "当前主导路线一句话说明（可选）"
}}

## 结局触发规则
除非系统明确要求生成结局，否则不要主动结束游戏。
当系统提示生成结局时，不返回 choices，改为：
{{"scene": "完整结局描述", "ending": "好结局/中立结局/坏结局", "log": "冒险终章"}}

## choices 规范
- 数量必须是 3 或 4 个，且彼此意图明显不同。
- 每个选项格式：
{{
  "text": "选项文本",
  "tendency": ["倾向标签1", "倾向标签2"],
  "is_key_decision": false,
  "consequence_hint": "后果预览（可选）",
  "check": null 或 {{
    "attribute": "strength|dexterity|constitution|intelligence|wisdom|charisma",
    "skill": "技能名（可选）",
    "difficulty": 8-20,
    "description": "检定描述（可选）"
  }},
  "check_optional": true,
  "check_prompt": "提示文字（可选）"
}}

## 检定与代价
- {profile.label}的检定应该优先服务于其场景冲突，不要生成脱离题材的万能挑战。
- consequence_hint 必须是该题材里的具体代价，例如人情债、名声受损、补给消耗、盟约破裂、旧伤复发，而不是空泛的“可能有风险”。
- 大约每 5 轮出现一次关键抉择，不要连续两轮都标记。

## 物品示例
- 只生成符合题材的物品变化，例如：{'、'.join(profile.item_archetypes[:4])}
- 禁止把另一种题材的典型物件带进来。

{build_route_tendency_mapping(profile)}

{UNIVERSAL_PROMPT_LITE}
"""


def build_memory_update_prompt(
    scenario_type: Optional[str],
    *,
    memory_content: str,
    current_round: int,
    scene: str,
    selected_choice: str,
    log_summary: str,
    check_result: str,
    relationship_changes: str,
    route_scores: str,
    ending_type: str,
) -> str:
    profile = get_scenario_profile(scenario_type)
    special_sections = "\n".join(f"## {section}\n（按本回合更新，保留长期线索）" for section in profile.memory_sections)
    return f"""你是一个游戏剧情记录与世界状态维护助手，专门维护【{profile.label}】题材的 memory.md。
返回结果会整体覆盖 memory.md，所以必须保留已有核心设定。

## 题材规则
- {profile.world_tone}
- {profile.story_focus}
- 特别关注：{'、'.join(profile.memory_sections)}

## 当前 memory.md 内容
{memory_content}

## 本回合新增信息
- 当前轮次：第 {current_round} 轮
- 场景描述：{scene}
- 玩家选择：{selected_choice}
- 本章概要：{log_summary}
- 检定结果：{check_result}
- 关系变化：{relationship_changes}
- 路线得分：{route_scores}
- 结局类型：{ending_type}

请按以下结构返回完整 markdown：
# 游戏记忆文档

## 场景类型
{profile.label}

## 世界观设定
（保留原文）

## 故事概要
（≤120字，更新近期局势）

## 关键事件
（原样保留已有内容，不要擅自改写）

## 世界状态
- 当前时间：
- 当前地点：
- 主角持有物：
- 主角状态：

## 主要角色
- 角色名（称号/势力）：当前位置、态度、与主角关系

{special_sections}

## 故事流程
（只在末尾追加本轮一行："第{current_round}轮：[场景一句话] → 玩家选择「{selected_choice}」→ [结果一句话]"）

## 未解决伏笔
（列出仍未回收的线索）

## 当前状态
（2-3句承上启下）
"""


def build_story_expansion_prompt(scenario_type: Optional[str], user_input: str) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是一个游戏策划，正在为【{profile.label}】生成一份本局 campaign brief。

## 题材约束
- 基调：{profile.world_tone}
- 文风方向：{profile.prose_style}
- 超凡边界：{profile.supernatural_rules}
- 核心冲突轴：{'、'.join(profile.conflict_axes)}
- 常见角色原型：{'、'.join(profile.character_archetypes)}
- 常见地点：{'、'.join(profile.location_pool)}
- 必须避免跑题：{profile.story_focus}

## 用户补充设定
{user_input or "（无额外补充）"}

请按以下 markdown 结构输出，不要 JSON：

# Campaign Brief

## 场景类型
{profile.label}

## 地区与时代感

## 势力格局

## 当前紧张局势

## 主角适合的身份方向
- 身份方向：
- 性格关键词：
- 初始处境：
- 核心驱动：

## 关键 NPC 原型
- 原型1：
- 原型2：
- 原型3：

## 第一幕起点
- 时间：
- 地点：
- 起始画面：
- 第一个抉择钩子：

## 本局禁用项或边界

## 本局特有名词表
- 名词：

## 可能的故事走向
"""


def build_player_generation_prompt(
    scenario_type: Optional[str], world_setting: str, campaign_brief: str = ""
) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是一个角色设计师，请为【{profile.label}】生成主角。

## 题材约束
- {profile.world_tone}
- {profile.prose_style}
- {profile.supernatural_rules}
- 角色原型参考：{'、'.join(profile.character_archetypes)}
- 种族/血统默认从这些合理范围内选择：{'、'.join(profile.player_races)}

## 本局设定补充
{world_setting or "（无）"}

## Campaign Brief
{campaign_brief or "（无）"}

要求：
1. 主角必须能放大题材冲突，而不是万能英雄。
2. 年龄 16-55；强项明显，弱项真实，属性总和 60-80。
3. 称号、背景、性格、核心动机都必须直接嵌入当前局势。
4. 技能 2-3 个，必须符合该题材，不要出现高魔法师模板。

请严格返回 JSON：
{{
  "name": "角色名",
  "age": 25,
  "gender": "男/女/其他",
  "race": "合理身份或血统",
  "title": "称号或职业",
  "appearance": "外貌描述",
  "background": "背景故事",
  "personality": "性格特点",
  "motivation": "核心动机",
  "strength": 12,
  "dexterity": 12,
  "constitution": 12,
  "intelligence": 12,
  "wisdom": 12,
  "charisma": 12,
  "skills": [
    {{
      "name": "技能名",
      "category": "combat|social|knowledge|survival",
      "level": 2,
      "description": "技能描述"
    }}
  ]
}}

{JSON_OUTPUT_RULES}
"""


def build_npc_list_prompt(
    scenario_type: Optional[str], world_setting: str, protagonist_info: str, count: int
) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是角色设计师，请为【{profile.label}】生成 {count} 个 NPC 名录。

## 题材约束
- 冲突轴：{'、'.join(profile.conflict_axes)}
- 角色原型：{'、'.join(profile.character_archetypes)}
- 不要串入另一种题材的名字、职位、组织风格。

## 本局设定补充
{world_setting or "（无）"}

## 主角信息
{protagonist_info}

请返回 JSON 数组，每项包含：
{{
  "name": "NPC姓名",
  "title": "称号或职业",
  "relation_to_protagonist": "与主角关系",
  "role_type": "antagonist|supporting|npc",
  "story_role": "导师/宿敌/同伴/中间人等"
}}

约束：
- 至少 1 个 antagonist、2 个 supporting。
- 名字、社会角色、势力归属必须有明显差异。
- 与主角关系要多样，优先让 NPC 嵌入该题材的政治/江湖结构。

{JSON_OUTPUT_RULES}
"""


def build_npc_detail_prompt(
    scenario_type: Optional[str],
    *,
    world_setting: str,
    protagonist_info: str,
    npc_name: str,
    npc_title: str,
    role_type: str,
    relation_to_protagonist: str,
    story_role: str,
) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是角色设计师，请为【{profile.label}】补全 NPC 设定。

题材约束：
- {profile.world_tone}
- {profile.supernatural_rules}
- 重点写该角色在社会关系网中的位置，而不是只写战斗力。

本局设定：
{world_setting or "（无）"}

主角信息：
{protagonist_info}

NPC 基础信息：
- 姓名：{npc_name}
- 称号：{npc_title}
- role_type：{role_type}
- 与主角关系：{relation_to_protagonist}
- 剧情定位：{story_role}

请严格返回 JSON：
{{
  "name": "{npc_name}",
  "age": 30,
  "gender": "合理设定",
  "race": "合理设定",
  "title": "{npc_title}",
  "role_type": "{role_type}",
  "appearance": "外貌描述",
  "background": "背景故事",
  "personality": "性格特点",
  "relation_to_protagonist": "{relation_to_protagonist}",
  "story_role": "{story_role}",
  "plot_connection": "与主线的具体关联",
  "faction": "所属势力",
  "social_status": "社会身份",
  "public_reputation": "外界如何看待此人",
  "taboos": ["禁忌1"],
  "attributes": {{
    "strength": 10,
    "dexterity": 10,
    "constitution": 10,
    "intelligence": 10,
    "wisdom": 10,
    "charisma": 10
  }},
  "skills": [
    {{
      "name": "技能名",
      "category": "combat|social|knowledge|survival",
      "level": 2,
      "description": "技能描述"
    }}
  ]
}}

{JSON_OUTPUT_RULES}
"""


def build_npc_dialogue_prompt(scenario_type: Optional[str]) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你正在扮演【{profile.label}】中的 NPC 与玩家对话。
必须保持题材口吻一致，不要出戏，不要透露自己是 AI。

题材文风：
- {profile.prose_style}
- {profile.story_focus}

## NPC 信息
- 姓名：{{npc_name}}
- 称号：{{npc_title}}
- 性格：{{npc_personality}}
- 背景：{{npc_background}}
- 与玩家关系：{{npc_relation}}

## 互动历史
{{relation_events}}

## 当前场景与近期主线
{{context}}

## 玩家本轮发言
{{player_message}}

输出 JSON：
{{"dialogue":"≤120字的回应","mood":"情绪（可选）","relationship_hint":"关系暗示（可选）"}}
"""


def build_novel_title_prompt(
    scenario_type: Optional[str],
    *,
    memory_content: str,
    event_ledger_overview: str,
    min_chapters: int,
    max_chapters: int,
) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是小说策划师，正在把【{profile.label}】游戏记录整理成小说纲要。
题材文风：{profile.prose_style}
题材重点：{profile.story_focus}

输入：
- memory_content: {memory_content}
- event_ledger_overview: {event_ledger_overview}
- min_chapters: {min_chapters}
- max_chapters: {max_chapters}

要求：
1. 标题与章节标题必须体现 {profile.label} 风格。
2. 章节概要只能引用台账中的事件。
3. 返回 JSON：{{"title":"总标题","chapters":[{{"chapter_num":1,"title":"标题","summary":"概要"}}]}}

{JSON_OUTPUT_RULES}
"""


def build_novel_incremental_plan_prompt(
    scenario_type: Optional[str],
    *,
    novel_title: str,
    existing_chapters_count: int,
    last_covered_round: int,
    existing_chapters_summary: str,
    memory_content: str,
    current_round: int,
    event_ledger_overview: str,
    min_chapters: int,
    max_chapters: int,
    start_chapter_num: int,
) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是小说策划师，正在为【{profile.label}】规划续写章节。
题材文风：{profile.prose_style}
题材重点：{profile.story_focus}

输入：
- novel_title: {novel_title}
- existing_chapters_count: {existing_chapters_count}
- last_covered_round: {last_covered_round}
- existing_chapters_summary: {existing_chapters_summary}
- memory_content: {memory_content}
- current_round: {current_round}
- event_ledger_overview: {event_ledger_overview}
- min_chapters: {min_chapters}
- max_chapters: {max_chapters}
- start_chapter_num: {start_chapter_num}

返回 JSON：{{"chapters":[{{"chapter_num":{start_chapter_num},"title":"标题","summary":"概要"}}]}}

{JSON_OUTPUT_RULES}
"""


def build_novel_chapter_prompt(
    scenario_type: Optional[str],
    *,
    novel_title: str,
    characters_digest: str,
    memory_content: str,
    previous_context: str,
    chapter_event_ledger: str,
    chapter_num: int,
    chapter_title: str,
    chapter_summary: str,
    continuation_requirement: str,
) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是小说作家，正在把【{profile.label}】游戏台账改写成小说章节。
文风要求：{profile.prose_style}
题材重点：{profile.story_focus}

输入：
- novel_title: {novel_title}
- characters_digest: {characters_digest}
- memory_content: {memory_content}
- previous_context: {previous_context}
- chapter_event_ledger: {chapter_event_ledger}
- chapter_num: {chapter_num}
- chapter_title: {chapter_title}
- chapter_summary: {chapter_summary}
- continuation_requirement: {continuation_requirement}

要求：
1. 章节标题和正文必须符合该题材。
2. 关键事件只能来自台账。
3. 可以润色环境、心理和无名角色反应。

{NOVEL_FIDELITY_RULES}
"""


def build_novel_ending_prompt(
    scenario_type: Optional[str],
    *,
    novel_title: str,
    characters_digest: str,
    memory_content: str,
    previous_context: str,
    unresolved_threads: str,
    ending_type: str,
    custom_description: str = "",
    route_leader: str,
    route_scores: str,
    final_rounds_ledger: str,
) -> str:
    profile = get_scenario_profile(scenario_type)
    return f"""你是小说作家，正在为【{profile.label}】创作终章。
文风要求：{profile.prose_style}
题材重点：{profile.story_focus}

输入：
- novel_title: {novel_title}
- characters_digest: {characters_digest}
- memory_content: {memory_content}
- previous_context: {previous_context}
- unresolved_threads: {unresolved_threads}
- ending_type: {ending_type}
- custom_description: {custom_description or "无"}
- route_leader: {route_leader}
- route_scores: {route_scores}
- final_rounds_ledger: {final_rounds_ledger}

要求：
1. 回收主要伏笔，但保留题材允许的苦涩与余味。
2. 终章必须把路线倾向翻译成 {profile.label} 的语境。
3. 不得凭空添加台账之外的关键反转。

{NOVEL_FIDELITY_RULES}
"""

