from typing import List, Dict, Optional
from app.utils.file_storage import load_memory, load_player, load_characters
from app.config import SYSTEM_PROMPT


MAX_MEMORY_CHARS = 3000
MAX_CHARACTERS = 8
MAX_CHARS_PER_CHARACTER = 300
MAX_RECENT_MESSAGES = 20


class PromptComposer:
    def __init__(self):
        pass

    def truncate_text(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...(已截断)"

    def get_memory_section(self) -> str:
        memory = load_memory()
        if not memory:
            return ""
        return self.truncate_text(memory, MAX_MEMORY_CHARS)

    def get_player_section(self) -> str:
        player = load_player()
        if not player:
            return ""

        lines = ["## 玩家角色信息\n"]
        lines.append(f"**姓名**: {player.get('name', '未知')}")
        lines.append(f"**称号**: {player.get('title', '')}")
        lines.append(f"**种族**: {player.get('race', '')} {player.get('gender', '')} {player.get('age', '')}岁")
        lines.append(f"**背景**: {player.get('background', '')[:200]}")

        lines.append("\n**属性**:")
        attrs = [
            ("力量", "strength"),
            ("敏捷", "dexterity"),
            ("体质", "constitution"),
            ("智力", "intelligence"),
            ("感知", "wisdom"),
            ("魅力", "charisma"),
        ]
        for name, key in attrs:
            val = player.get(key, 10)
            lines.append(f"- {name}: {val}")

        if player.get("skills"):
            lines.append("\n**技能**:")
            for skill in player["skills"]:
                lines.append(f"- {skill.get('name')} Lv.{skill.get('level', 1)}: {skill.get('description', '')}")

        result = "\n".join(lines)
        return self.truncate_text(result, MAX_CHARS_PER_CHARACTER * 2)

    def get_characters_section(self) -> str:
        characters = load_characters()
        if not characters:
            return ""

        characters = sorted(characters, key=lambda c: c.get("importance", 0), reverse=True)
        characters = characters[:MAX_CHARACTERS]

        lines = ["## 已出场角色\n"]

        for char in characters:
            name = char.get("name", "未知")
            title = char.get("title", "")
            description = char.get("description", "")
            if title:
                line = f"- {name}, {title}: {description}"
            else:
                line = f"- {name}: {description}"
            line = self.truncate_text(line, MAX_CHARS_PER_CHARACTER)
            lines.append(line)

        result = "\n".join(lines)
        return self.truncate_text(result, MAX_CHARACTERS * MAX_CHARS_PER_CHARACTER)

    def get_last_check_context(self, turn_context: Optional[Dict]) -> str:
        if not turn_context or "last_check" not in turn_context:
            return ""
        check = turn_context["last_check"]
        if not check:
            return ""

        result = f"""
## 上一轮检定结果

检定信息：
- 属性: {check.get('attribute', '未知')}
- 难度: {check.get('difficulty', '未知')}
- 掷骰: {check.get('roll', 0)}
- 总计: {check.get('total', 0)}
- 结果: {'成功' if check.get('success') else '失败'}
- 叙述: {check.get('narrative', '')}

请根据这个检定结果继续推进剧情。
"""
        return result

    def get_tendency_section(self, tendency_data: Optional[Dict] = None) -> str:
        if not tendency_data:
            return ""

        dimensions = [
            ("勇敢", "谨慎"),
            ("善良", "冷酷"),
            ("理性", "感性"),
            ("正义", "自利"),
            ("仁慈", "残忍"),
            ("坦诚", "狡诈"),
        ]

        lines = ["## 玩家性格画像\n"]
        lines.append("根据玩家之前的选择，其性格倾向如下：")

        for pos, neg in dimensions:
            pos_score = tendency_data.get(pos, 0)
            neg_score = tendency_data.get(neg, 0)
            if pos_score > neg_score:
                diff = pos_score - neg_score
                if diff >= 10:
                    lines.append(f"- **{pos}**（强烈）: 得分 +{diff}")
                elif diff >= 5:
                    lines.append(f"- **{pos}**（明显）: 得分 +{diff}")
                else:
                    lines.append(f"- **{pos}**（轻微）: 得分 +{diff}")
            elif neg_score > pos_score:
                diff = neg_score - pos_score
                if diff >= 10:
                    lines.append(f"- **{neg}**（强烈）: 得分 +{diff}")
                elif diff >= 5:
                    lines.append(f"- **{neg}**（明显）: 得分 +{diff}")
                else:
                    lines.append(f"- **{neg}**（轻微）: 得分 +{diff}")
            else:
                lines.append(f"- {pos}/{neg}: 中立")

        lines.append("\n请根据玩家的性格倾向调整剧情走向和NPC的反应。")
        result = "\n".join(lines)
        return self.truncate_text(result, 500)

    def get_route_section(self, turn_context: Optional[Dict]) -> str:
        if not turn_context or "route_scores" not in turn_context:
            return ""

        scores = turn_context["route_scores"]
        leader = turn_context.get("route_leader", "")

        if not scores:
            return ""

        lines = ["## 结局路线追踪\n"]
        lines.append("当前五个结局路线的积分为：")
        lines.append(f"- 救赎(redemption): {scores.get('redemption', 0)}")
        lines.append(f"- 权力(power): {scores.get('power', 0)}")
        lines.append(f"- 牺牲(sacrifice): {scores.get('sacrifice', 0)}")
        lines.append(f"- 背叛(betrayal): {scores.get('betrayal', 0)}")
        lines.append(f"- 隐退(retreat): {scores.get('retreat', 0)}")

        if leader:
            lines.append(f"\n当前主导路线为：{leader}。如果主导路线分数较高，请务必在返回JSON中加入`ending_omen`字段返回一段沉浸式的结局前兆暗示，以及`route_hint`字段一句话说明该路线的核心特质。")

        return "\n".join(lines)

    def compose(
        self,
        messages: List[Dict],
        extra_prompt: str = "",
        turn_context: Optional[Dict] = None,
        tendency_data: Optional[Dict] = None,
    ) -> List[Dict]:
        memory_section = self.get_memory_section()
        player_section = self.get_player_section()
        characters_section = self.get_characters_section()
        check_section = self.get_last_check_context(turn_context)
        tendency_section = self.get_tendency_section(tendency_data)
        route_section = self.get_route_section(turn_context)

        context_parts = []
        if memory_section:
            context_parts.append(memory_section)
        if player_section:
            context_parts.append(player_section)
        if characters_section:
            context_parts.append(characters_section)
        if tendency_section:
            context_parts.append(tendency_section)
        if check_section:
            context_parts.append(check_section)
        if route_section:
            context_parts.append(route_section)

        context_text = "\n\n".join(context_parts)

        if context_text:
            context_text += "\n\n---\n\n以上是当前游戏的背景和记忆信息，请根据以上信息和玩家的选择继续生成剧情。\n"

        recent_messages = messages[-MAX_RECENT_MESSAGES:] if len(messages) > MAX_RECENT_MESSAGES else messages

        full_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context_text},
        ] + recent_messages

        if extra_prompt:
            full_messages.append({"role": "system", "content": extra_prompt})

        return full_messages
