import re
from typing import Dict, List, Optional, Tuple

from app.config import MAX_MEMORY_CHARS, MAX_RECENT_MESSAGES, ROUTE_TENDENCY_MAPPING, SYSTEM_PROMPT
from app.game_context import GameContext


MAX_CHARACTERS = 8
MAX_CHARS_PER_CHARACTER = 300


class PromptComposer:
    def __init__(self, memory_repository, player_repository, character_repository):
        self.memory_repository = memory_repository
        self.player_repository = player_repository
        self.character_repository = character_repository

    def truncate_text(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...(已截断)"

    def _parse_memory_sections(self, memory: str) -> List[Dict[str, str]]:
        sections = []
        pattern = re.compile(r'^## (.+)$', re.MULTILINE)
        matches = list(pattern.finditer(memory))
        for i, match in enumerate(matches):
            header = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(memory)
            content = memory[start:end].strip()
            sections.append({"header": header, "content": content})
        return sections

    def get_memory_section(self, ctx: Optional[GameContext]) -> str:
        memory = self.memory_repository.load_text(ctx)
        if not memory:
            return ""

        sections = self._parse_memory_sections(memory)
        if not sections:
            return self.truncate_text(memory, MAX_MEMORY_CHARS)

        priority_headers = ["世界观设定", "关键事件", "世界状态", "当前状态"]
        high_sections = []
        other_sections = []
        for sec in sections:
            header_clean = sec["header"].lstrip("🔑").strip()
            if header_clean in priority_headers:
                high_sections.append(sec)
            else:
                other_sections.append(sec)

        core = "\n\n".join(f"## {s['header']}\n{s['content']}" for s in high_sections)
        remaining = MAX_MEMORY_CHARS - len(core)

        if remaining > 0:
            flow_parts = []
            chars_used = 0
            for sec in other_sections:
                block = f"## {sec['header']}\n{sec['content']}"
                if chars_used + len(block) <= remaining:
                    flow_parts.append(block)
                    chars_used += len(block)
                else:
                    available = remaining - chars_used - 30
                    if available > 100:
                        truncated = self.truncate_text(block, available)
                        flow_parts.append(truncated)
                    else:
                        flow_parts.append(f"## {sec['header']}\n...(早期记录已归档)")
                    break
            if flow_parts:
                core += "\n\n" + "\n\n".join(flow_parts)

        return core

    def get_player_section(self, ctx: Optional[GameContext]) -> str:
        player = self.player_repository.load(ctx)
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

    def get_characters_section(self, ctx: Optional[GameContext]) -> str:
        characters = self.character_repository.load_all(ctx)
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

    def _summarize_old_messages(
        self, messages: List[Dict], keep_recent: int
    ) -> Tuple[List[Dict], Optional[str]]:
        if len(messages) <= keep_recent:
            return messages, None

        old = messages[:-keep_recent]
        recent = messages[-keep_recent:]

        summary_lines = []
        for msg in old:
            raw = msg.get("content", "")
            if isinstance(raw, str):
                text = raw
            elif isinstance(raw, list):
                text = " ".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in raw
                )
            else:
                text = str(raw)

            if msg.get("role") == "user":
                summary_lines.append(f"玩家选择: {text[:60]}")
            elif msg.get("role") == "assistant":
                summary_lines.append(f"事件: {text[:80]}")
            else:
                summary_lines.append(f"消息: {text[:60]}")

        summary = "## 历史摘要\n" + "\n".join(summary_lines)
        return recent, summary

    def compose(
        self,
        ctx: Optional[GameContext],
        messages: List[Dict],
        extra_prompt: str = "",
        turn_context: Optional[Dict] = None,
        tendency_data: Optional[Dict] = None,
    ) -> List[Dict]:
        memory_section = self.get_memory_section(ctx)
        player_section = self.get_player_section(ctx)
        characters_section = self.get_characters_section(ctx)
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

        recent_messages, summary = self._summarize_old_messages(messages, MAX_RECENT_MESSAGES)

        full_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": ROUTE_TENDENCY_MAPPING},
            {"role": "user", "content": context_text},
        ]

        if summary:
            full_messages.append({"role": "system", "content": summary})

        full_messages.extend(recent_messages)

        if extra_prompt:
            full_messages.append({"role": "system", "content": extra_prompt})

        return full_messages
