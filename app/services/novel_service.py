import json
import logging
import os
import re
import shutil
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import (
    NOVEL_CHAPTER_PROMPT,
    NOVEL_ENDING_PROMPT,
    NOVEL_GENERATION_PROMPT,
    NOVEL_INCREMENTAL_PLAN_PROMPT,
    NOVEL_TITLE_PROMPT,
)
from app.game_context import GameContext

logger = logging.getLogger(__name__)

_DEFAULT_ROUTE_SCORES = {
    "redemption": 0,
    "power": 0,
    "sacrifice": 0,
    "betrayal": 0,
    "retreat": 0,
}


class NovelService:
    def __init__(
        self,
        memory_repository,
        save_repository,
        novel_repository,
        llm_adapter,
        player_repository,
        character_repository,
    ):
        self.memory_repository = memory_repository
        self.save_repository = save_repository
        self.novel_repository = novel_repository
        self.llm_adapter = llm_adapter
        self.player_repository = player_repository
        self.character_repository = character_repository

    def _load_state(self, ctx: Optional[GameContext]) -> Optional[Dict[str, Any]]:
        return self.novel_repository.load_current_state(ctx)

    def _save_state(self, ctx: GameContext, state: Dict[str, Any]) -> None:
        state["updated_at"] = datetime.now().isoformat()
        self.novel_repository.save_current_state(ctx, state)

    def _init_state(self, ctx: GameContext, title: str) -> Dict[str, Any]:
        state = {
            "title": title,
            "status": "in_progress",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_covered_round": 0,
            "total_game_rounds": 0,
            "chapters": [],
            "pending_plan": None,
            "ending_chapter": None,
        }
        self._save_state(ctx, state)
        return state

    def _existing_chapters_summary(self, state: Dict[str, Any]) -> str:
        if not state["chapters"]:
            return "（无已有章节）"
        lines = []
        for chapter in state["chapters"]:
            rounds = chapter.get("covers_rounds", [])
            rounds_str = (
                f"（覆盖第{rounds[0]}-{rounds[1]}轮）" if len(rounds) == 2 else ""
            )
            lines.append(
                f"- 第{chapter['chapter_num']}章《{chapter['title']}》{rounds_str}：{chapter.get('summary', '')}"
            )
        return "\n".join(lines)

    def _build_characters_digest(
        self, ctx: Optional[GameContext], max_chars: int = 1800
    ) -> str:
        lines: List[str] = []
        player = self.player_repository.load(ctx) if ctx else None
        if player:
            name = player.get("name", "未知")
            title = player.get("title", "")
            race = player.get("race", "")
            age = player.get("age", "")
            personality = (player.get("personality") or "")[:80]
            background = (player.get("background") or "")[:200]
            motivation = ""
            if "核心动机" in background:
                background = background.split("核心动机")[0].strip()
                motivation = (
                    (player.get("background") or "").split("核心动机", 1)[-1].lstrip("：: ")[:80]
                )
            head = f"【主角】{name}"
            if title:
                head += f"（{title}）"
            extras = []
            if race:
                extras.append(f"{race}")
            if age:
                extras.append(f"{age}岁")
            if extras:
                head += f"，{'/'.join(extras)}"
            lines.append(head)
            if personality:
                lines.append(f"  性格：{personality}")
            if background:
                lines.append(f"  背景：{background}")
            if motivation:
                lines.append(f"  动机：{motivation}")

        characters = self.character_repository.load_all(ctx) if ctx else []
        characters = sorted(characters, key=lambda c: c.get("importance", 0), reverse=True)
        included = 0
        for char in characters:
            if included >= 8:
                break
            role = char.get("role_type", "npc")
            if role == "npc" and included >= 4:
                continue
            name = char.get("name", "未知")
            title = char.get("title", "")
            role_cn = {
                "antagonist": "主反派",
                "supporting": "重要配角",
                "protagonist": "主角",
                "npc": "配角",
            }.get(role, "配角")
            head = f"【{role_cn}】{name}"
            if title:
                head += f"（{title}）"
            lines.append(head)

            personality = char.get("personality")
            if isinstance(personality, dict):
                traits = personality.get("traits") or []
                style = personality.get("dialogue_style", "")
                bits = []
                if traits:
                    bits.append("、".join(traits[:4]))
                if style:
                    bits.append(f"语气：{style}")
                if bits:
                    lines.append(f"  性格：{' / '.join(bits)}")
            elif isinstance(personality, str) and personality:
                lines.append(f"  性格：{personality[:80]}")

            background = char.get("background")
            if isinstance(background, dict):
                backstory = (background.get("backstory") or "")[:160]
                motivations = (background.get("motivations") or "")[:80]
                if backstory:
                    lines.append(f"  背景：{backstory}")
                if motivations:
                    lines.append(f"  动机：{motivations}")
            elif isinstance(background, str) and background:
                lines.append(f"  背景：{background[:160]}")

            relation = char.get("relation_to_protagonist")
            if relation:
                lines.append(f"  与主角：{relation[:80]}")
            included += 1

        if not lines:
            return "（角色档案缺失，请凭 memory_content 推断人物，但不要捏造关键设定）"

        digest = "\n".join(lines)
        if len(digest) > max_chars:
            digest = digest[:max_chars] + "\n...（已截断）"
        return digest

    def _build_event_ledger(
        self,
        ctx: Optional[GameContext],
        *,
        round_start: int = 1,
        round_end: Optional[int] = None,
        compact: bool = False,
        max_chars: int = 8000,
    ) -> str:
        history = self.save_repository.load_history(ctx) if ctx else []
        main_logs: List[Dict[str, Any]] = []

        if history:
            best = max(history, key=lambda s: len(s.get("logs", [])))
            raw_logs: List[Any] = best.get("logs", [])
            for entry in raw_logs:
                if not isinstance(entry, dict):
                    continue
                log_text: str = entry.get("log") or ""
                if log_text.startswith("\U0001F31F 命运前兆:") or log_text.startswith(
                    "\U0001F9ED 路线关注:"
                ):
                    continue
                if not log_text:
                    continue
                main_logs.append(entry)

        if not main_logs:
            return ""

        effective_end = round_end if round_end is not None else len(main_logs)
        effective_end = min(effective_end, len(main_logs))

        lines: List[str] = []
        for i in range(round_start - 1, effective_end):
            entry = main_logs[i]
            round_num = i + 1
            scene = ((entry.get("scene") or "").split("\n")[0])[:80]
            choice = (entry.get("selectedChoice") or "（无记录）")[:60]
            log_text = (entry.get("log") or "")[:60]

            if compact:
                lines.append(f"第{round_num}轮：{log_text}（玩家选：{choice}）")
            else:
                block_parts = [f"【第{round_num}轮】"]
                if scene:
                    block_parts.append(f"  场景：{scene}")
                block_parts.append(f"  玩家选择：{choice}")
                block_parts.append(f"  结果概述：{log_text}")
                lines.append("\n".join(block_parts))

        if not lines:
            return ""

        result = "\n".join(lines)

        if len(result) > max_chars:
            keep = 5
            if len(lines) > keep * 2:
                head = lines[:keep]
                tail = lines[-keep:]
                omitted = len(lines) - keep * 2
                mid_note = (
                    f"...（中间第{round_start + keep}至第{effective_end - keep}轮共 {omitted} "
                    "轮概略省略，主线以下方首尾轮次为准）..."
                )
                result = "\n".join(head) + "\n" + mid_note + "\n" + "\n".join(tail)
            else:
                result = result[:max_chars]

        return result

    def _extract_chapter_events(
        self,
        ctx: Optional[GameContext],
        memory_content: str,
        round_start: int,
        round_end: int,
    ) -> str:
        if round_end < round_start:
            return "（本章无明确游戏事件，请基于章节概要发挥）"

        ledger = self._build_event_ledger(
            ctx, round_start=round_start, round_end=round_end, compact=False
        )
        if ledger:
            return ledger

        if not memory_content:
            return "（本章无明确游戏事件，请基于章节概要发挥）"

        in_flow = False
        flow_lines: List[str] = []
        for raw in memory_content.splitlines():
            line = raw.rstrip()
            if line.startswith("## "):
                heading = line[3:].strip()
                in_flow = "故事流程" in heading
                continue
            if in_flow and line.strip():
                flow_lines.append(line)

        if not flow_lines:
            return "（memory.md 中没有故事流程段，请基于章节概要发挥）"

        round_pattern = re.compile(r"第\s*(\d+)(?:\s*[-–到至]\s*(\d+))?\s*轮")
        matched: List[str] = []
        for line in flow_lines:
            m = round_pattern.search(line)
            if not m:
                continue
            try:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else start
            except (TypeError, ValueError):
                continue
            if end < round_start or start > round_end:
                continue
            matched.append(line.strip().lstrip("-").strip())

        if not matched:
            return (
                f"（未在 memory 中找到第 {round_start}-{round_end} 轮的明确条目，"
                "请基于章节概要发挥，但不要与已有事件矛盾）"
            )

        return "\n".join(f"- {line}" for line in matched)

    def _extract_unresolved_threads(self, memory_content: str) -> str:
        if not memory_content:
            return "（无显式伏笔）"
        in_section = False
        captured: List[str] = []
        for raw in memory_content.splitlines():
            line = raw.rstrip()
            if line.startswith("## "):
                in_section = "未解决伏笔" in line
                continue
            if in_section:
                if line.strip():
                    captured.append(line.strip())
        if not captured:
            return "（无显式伏笔，请基于 memory_content 自行识别需要回收的线索）"
        return "\n".join(captured)

    def _extract_route_scores(self, ctx: Optional[GameContext]) -> Dict[str, Any]:
        scores = dict(_DEFAULT_ROUTE_SCORES)
        if not ctx:
            return {"scores": scores, "leader": ""}
        try:
            saves = self.save_repository.list_saves(ctx) or []
        except Exception:
            saves = []
        for save in saves:
            rs = save.get("route_scores")
            if isinstance(rs, dict) and rs:
                for key in scores:
                    val = rs.get(key)
                    if isinstance(val, (int, float)):
                        scores[key] = val
                break
        leader = ""
        max_score = -1
        for key, val in scores.items():
            if val > max_score:
                max_score = val
                leader = key
        if max_score <= 0:
            leader = ""
        return {"scores": scores, "leader": leader}

    def calculate_chapter_range(self, game_rounds: int = 0) -> tuple:
        effective_rounds = game_rounds or 10
        min_chapters = max(2, int(effective_rounds * 0.30))
        max_chapters = max(min_chapters + 1, int(effective_rounds * 0.50))
        return min(min_chapters, 15), min(max_chapters, 20), effective_rounds

    def get_novel_progress(
        self, ctx: Optional[GameContext], current_round: int = 0
    ) -> Dict[str, Any]:
        _ = current_round
        state = self._load_state(ctx)
        current_round = self.save_repository.get_round_count(ctx) if ctx else 0

        if state is None:
            return {
                "has_novel": False,
                "title": None,
                "chapters_count": 0,
                "chapters": [],
                "last_covered_round": 0,
                "current_round": current_round,
                "can_continue": current_round > 0,
                "status": None,
            }

        new_rounds = current_round - state.get("last_covered_round", 0)
        return {
            "has_novel": True,
            "title": state.get("title", ""),
            "chapters_count": len(state.get("chapters", [])),
            "chapters": state.get("chapters", []),
            "last_covered_round": state.get("last_covered_round", 0),
            "current_round": current_round,
            "new_rounds": new_rounds,
            "can_continue": new_rounds > 0,
            "status": state.get("status", "in_progress"),
        }

    def get_novel_content(self, ctx: Optional[GameContext]) -> Dict[str, Any]:
        state = self._load_state(ctx)
        if ctx is None or state is None:
            return {"has_novel": False, "content": "", "title": ""}

        content = self.novel_repository.load_current_merged_novel(ctx)
        if not content:
            return {"has_novel": False, "content": "", "title": ""}

        return {
            "has_novel": True,
            "content": content,
            "title": state.get("title", ""),
            "chapters_count": len(state.get("chapters", [])),
            "status": state.get("status", "in_progress"),
        }

    def reset_novel(self, ctx: GameContext) -> Dict[str, Any]:
        novel_dir = self.novel_repository.paths.current_novel_dir(ctx)
        if os.path.exists(novel_dir):
            shutil.rmtree(novel_dir)
            return {"success": True, "message": "小说已重置，下次生成将重新规划"}
        return {"success": True, "message": "无已有小说，无需重置"}

    async def generate_incremental(
        self, ctx: GameContext, ending_type: str = "", current_round: int = 0
    ) -> Dict[str, Any]:
        _ = current_round
        memory_content = self.memory_repository.load_text(ctx)
        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        current_round = self.save_repository.get_round_count(ctx)
        if current_round <= 0:
            current_round = 1

        state = self._load_state(ctx)
        if state is None:
            return await self._generate_fresh(ctx, memory_content, current_round, ending_type)

        last_covered = state.get("last_covered_round", 0)
        if current_round <= last_covered and not ending_type:
            merged = self._merge_current(ctx)
            return {
                "success": True,
                "mode": "no_change",
                "message": f"没有新剧情需要续写（已覆盖到第{last_covered}轮）",
                "novel_content": merged["novel_content"],
                "title": state.get("title", ""),
                "total_chapters": len(state.get("chapters", [])),
            }

        return await self._generate_continuation(
            ctx, state, memory_content, current_round, ending_type
        )

    async def _generate_fresh(
        self,
        ctx: GameContext,
        memory_content: str,
        current_round: int,
        ending_type: str = "",
    ) -> Dict[str, Any]:
        min_chapters, max_chapters, _ = self.calculate_chapter_range(current_round)
        event_ledger_overview = self._build_event_ledger(ctx, compact=True) or "（暂无历史台账）"
        plan_data = await self.llm_adapter.generate_json(
            ctx=ctx,
            prompt=NOVEL_TITLE_PROMPT.format(
                memory_content=memory_content,
                event_ledger_overview=event_ledger_overview,
                min_chapters=min_chapters,
                max_chapters=max_chapters,
            ),
            system_prompt="你是一个专业的小说策划师。",
            timeout=600,
            method_name="plan_incremental_novel",
        )
        self._validate_plan(plan_data)

        title = plan_data["title"]
        state = self._init_state(ctx, title)
        state["total_game_rounds"] = current_round
        self.novel_repository.save_current_plan(ctx, plan_data)

        chapters_generated = await self._generate_chapters_from_plan(
            ctx=ctx,
            plan_chapters=plan_data["chapters"],
            title=title,
            memory_content=memory_content,
            state=state,
            from_round=1,
            to_round=current_round,
        )

        if ending_type:
            await self._append_ending(ctx, state, title, memory_content, ending_type)

        merged = self._merge_current(ctx)
        return {
            "success": True,
            "mode": "fresh",
            "title": title,
            "total_chapters": len(state["chapters"]),
            "novel_content": merged["novel_content"],
            "chapters_generated": chapters_generated,
        }

    async def _generate_continuation(
        self,
        ctx: GameContext,
        state: Dict[str, Any],
        memory_content: str,
        current_round: int,
        ending_type: str = "",
    ) -> Dict[str, Any]:
        last_covered = state.get("last_covered_round", 0)
        new_rounds = current_round - last_covered
        title = state.get("title", "未命名小说")

        min_chapters = min(max(1, int(new_rounds * 0.30)), 8)
        max_chapters = min(max(min_chapters + 1, int(new_rounds * 0.50)), 10)
        start_chapter_num = len(state["chapters"]) + 1
        new_event_ledger = (
            self._build_event_ledger(
                ctx, round_start=last_covered + 1, round_end=current_round, compact=True
            )
            or "（暂无新轮次台账）"
        )

        plan_data = await self.llm_adapter.generate_json(
            ctx=ctx,
            prompt=NOVEL_INCREMENTAL_PLAN_PROMPT.format(
                novel_title=title,
                existing_chapters_count=len(state["chapters"]),
                last_covered_round=last_covered,
                existing_chapters_summary=self._existing_chapters_summary(state),
                memory_content=memory_content,
                current_round=current_round,
                min_chapters=min_chapters,
                max_chapters=max_chapters,
                start_chapter_num=start_chapter_num,
                event_ledger_overview=new_event_ledger,
            ),
            system_prompt="你是一个专业的小说策划师。",
            timeout=600,
            method_name="plan_novel_continuation",
        )

        if not plan_data or "chapters" not in plan_data or not plan_data["chapters"]:
            raise Exception("续写规划失败：LLM返回数据缺少chapters字段")

        state["total_game_rounds"] = current_round
        new_chapters = await self._generate_chapters_from_plan(
            ctx=ctx,
            plan_chapters=plan_data["chapters"],
            title=title,
            memory_content=memory_content,
            state=state,
            from_round=last_covered + 1,
            to_round=current_round,
        )

        if ending_type:
            await self._append_ending(ctx, state, title, memory_content, ending_type)

        merged = self._merge_current(ctx)
        return {
            "success": True,
            "mode": "continuation",
            "title": title,
            "total_chapters": len(state["chapters"]),
            "new_chapters": new_chapters,
            "novel_content": merged["novel_content"],
        }

    async def _generate_chapters_from_plan(
        self,
        ctx: GameContext,
        plan_chapters: List[Dict],
        title: str,
        memory_content: str,
        state: Dict[str, Any],
        from_round: int,
        to_round: int,
    ) -> int:
        chapters_dir = self.novel_repository.paths.current_novel_chapters_dir(ctx)
        generated = 0
        total_plan = len(plan_chapters)
        rounds_per_chapter = (
            max(1, (to_round - from_round + 1) / total_plan) if total_plan > 0 else 1
        )
        characters_digest = self._build_characters_digest(ctx)

        for index, chapter in enumerate(plan_chapters):
            chapter_num = chapter.get("chapter_num", len(state["chapters"]) + 1)
            chapter_title = chapter.get("title", f"第{chapter_num}章")
            chapter_summary = chapter.get("summary", chapter.get("outline", ""))
            previous_context, continuation_requirement = self._get_previous_context(
                chapters_dir
            )

            round_start = int(from_round + index * rounds_per_chapter)
            round_end = int(from_round + (index + 1) * rounds_per_chapter - 1)
            if index == total_plan - 1:
                round_end = to_round

            chapter_event_ledger = self._extract_chapter_events(
                ctx, memory_content, round_start, round_end
            )

            prompt = NOVEL_CHAPTER_PROMPT.format(
                novel_title=title,
                characters_digest=characters_digest,
                memory_content=memory_content,
                previous_context=previous_context,
                chapter_event_ledger=chapter_event_ledger,
                chapter_num=chapter_num,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                continuation_requirement=continuation_requirement,
            )

            try:
                content = await self.llm_adapter.generate_text(
                    ctx=ctx,
                    prompt=prompt,
                    system_prompt="你是一个专业的小说作家。",
                    timeout=600,
                    method_name="generate_novel_chapter",
                )
                filename = f"chapter_{chapter_num:02d}.md"
                self.novel_repository.save_current_chapter(ctx, filename, content)

                state["chapters"].append(
                    {
                        "chapter_num": chapter_num,
                        "title": chapter_title,
                        "summary": chapter_summary,
                        "covers_rounds": [round_start, round_end],
                        "generated_at": datetime.now().isoformat(),
                        "file": filename,
                    }
                )
                state["last_covered_round"] = to_round
                self._save_state(ctx, state)
                generated += 1
            except Exception as e:
                logger.error("第%s章生成失败: %s", chapter_num, e)
                continue

        return generated

    async def _append_ending(
        self,
        ctx: GameContext,
        state: Dict[str, Any],
        title: str,
        memory_content: str,
        ending_type: str,
    ) -> None:
        chapters_dir = self.novel_repository.paths.current_novel_chapters_dir(ctx)
        previous_context, _ = self._get_previous_context(chapters_dir)
        characters_digest = self._build_characters_digest(ctx)
        unresolved_threads = self._extract_unresolved_threads(memory_content)
        route_info = self._extract_route_scores(ctx)
        final_rounds_ledger = self._build_event_ledger(ctx, compact=False) or "（暂无台账）"
        prompt = NOVEL_ENDING_PROMPT.format(
            novel_title=title,
            characters_digest=characters_digest,
            memory_content=memory_content,
            previous_context=previous_context,
            unresolved_threads=unresolved_threads,
            ending_type=ending_type,
            route_leader=route_info["leader"] or "未明确",
            route_scores=json.dumps(route_info["scores"], ensure_ascii=False),
            final_rounds_ledger=final_rounds_ledger,
        )
        content = await self.llm_adapter.generate_text(
            ctx=ctx,
            prompt=prompt,
            system_prompt="你是一个专业的小说作家。",
            timeout=600,
            method_name="generate_novel_ending",
        )
        self.novel_repository.save_current_chapter(ctx, "ending.md", content)
        state["ending_chapter"] = {
            "title": "终章",
            "ending_type": ending_type,
            "generated_at": datetime.now().isoformat(),
            "file": "ending.md",
        }
        state["status"] = "completed"
        self._save_state(ctx, state)

    def _get_previous_context(self, chapters_dir: str) -> tuple:
        if not os.path.exists(chapters_dir):
            return "（这是第一章，没有前文）", "这是开篇章节，需要引人入胜的开头"

        files = sorted(name for name in os.listdir(chapters_dir) if name.endswith(".md"))
        if not files:
            return "（这是第一章，没有前文）", "这是开篇章节，需要引人入胜的开头"

        last_content = self.novel_repository.load_text(os.path.join(chapters_dir, files[-1]))
        tail = last_content[-1000:] if len(last_content) > 1000 else last_content
        return (
            f"上一章内容摘要（用于衔接）：\n...{tail}",
            "本章开头需要与上一章内容自然衔接",
        )

    def _merge_current(self, ctx: GameContext) -> Dict[str, Any]:
        state = self._load_state(ctx)
        chapters_dir = self.novel_repository.paths.current_novel_chapters_dir(ctx)
        title = state.get("title", "未命名小说") if state else "未命名小说"
        chapter_files = sorted(
            name for name in os.listdir(chapters_dir) if name.endswith(".md")
        ) if os.path.exists(chapters_dir) else []
        if not chapter_files:
            return {"novel_content": "", "total_chapters": 0}

        merged = f"# {title}\n\n"
        for chapter_file in chapter_files:
            chapter_path = os.path.join(chapters_dir, chapter_file)
            merged += self.novel_repository.load_text(chapter_path) + "\n\n"

        novel_path = self.novel_repository.save_current_merged_novel(ctx, merged)
        return {
            "novel_content": merged,
            "total_chapters": len(chapter_files),
            "novel_path": novel_path,
        }

    def _validate_plan(self, plan_data: Any) -> None:
        if plan_data is None:
            raise Exception("LLM返回了null内容")
        if not isinstance(plan_data, dict):
            raise Exception(f"LLM返回格式错误：期望JSON对象，实际为{type(plan_data)}")
        if "title" not in plan_data:
            raise Exception(f"LLM返回数据缺少title字段: {str(plan_data)[:200]}")
        if "chapters" not in plan_data:
            raise Exception(f"LLM返回数据缺少chapters字段: {str(plan_data)[:200]}")
        if not isinstance(plan_data["chapters"], list) or len(plan_data["chapters"]) == 0:
            raise Exception("LLM返回数据chapters为空")

    async def generate_full_novel(self, ctx: GameContext) -> dict:
        warnings.warn(
            "NovelService.generate_full_novel is deprecated; use generate_incremental instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.warning("generate_full_novel is deprecated; use generate_incremental.")
        memory_content = self.memory_repository.load_text(ctx)
        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        novel_content = await self.llm_adapter.generate_text(
            ctx=ctx,
            prompt=NOVEL_GENERATION_PROMPT.format(
                memory_content=memory_content,
                min_chapters=3,
                max_chapters=15,
            ),
            system_prompt="你是一个专业的小说作家。",
            timeout=600,
            method_name="generate_full_novel",
        )

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        novel_folder = f"novel-{timestamp}"
        novel_path = self.novel_repository.save_legacy_merged_novel(
            ctx, novel_folder, novel_content
        )
        return {
            "novel_folder": novel_folder,
            "novel_path": novel_path,
            "novel_content": novel_content,
        }

    async def plan_novel(self, ctx: GameContext) -> dict:
        memory_content = self.memory_repository.load_text(ctx)
        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        min_chapters, max_chapters, game_rounds = self.calculate_chapter_range(
            self.save_repository.get_round_count(ctx)
        )
        event_ledger_overview = self._build_event_ledger(ctx, compact=True) or "（暂无历史台账）"
        plan_data = await self.llm_adapter.generate_json(
            ctx=ctx,
            prompt=NOVEL_TITLE_PROMPT.format(
                memory_content=memory_content,
                event_ledger_overview=event_ledger_overview,
                min_chapters=min_chapters,
                max_chapters=max_chapters,
            ),
            system_prompt="你是一个专业的小说策划师。",
            timeout=600,
            method_name="plan_legacy_novel",
        )
        self._validate_plan(plan_data)

        plan_data["game_rounds"] = game_rounds
        plan_data["chapter_range"] = {"min": min_chapters, "max": max_chapters}
        plan_data["total_chapters"] = plan_data.get("total_chapters") or len(
            plan_data["chapters"]
        )

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        novel_folder = f"novel-{timestamp}"
        self.novel_repository.save_legacy_plan(ctx, novel_folder, plan_data)

        return {
            "novel_folder": novel_folder,
            "plan": plan_data,
            "game_rounds": game_rounds,
            "chapter_range": {"min": min_chapters, "max": max_chapters},
        }

    async def generate_chapter(
        self,
        ctx: GameContext,
        novel_folder: str,
        chapter_num: int,
        chapter_title: str,
        chapter_summary: str,
        ending_type: str = "",
    ) -> dict:
        memory_content = self.memory_repository.load_text(ctx)
        if not memory_content:
            raise Exception("memory.md不存在")

        is_current = (novel_folder == "current" or novel_folder == "")
        if is_current:
            state = self._load_state(ctx)
            novel_title = state.get("title", "未命名小说") if state else "未命名小说"
            chapters_dir = self.novel_repository.paths.current_novel_chapters_dir(ctx)
        else:
            plan_data = self.novel_repository.load_legacy_plan(ctx, novel_folder)
            novel_title = plan_data.get("title", "未命名小说")
            chapters_dir = self.novel_repository.legacy_chapters_dir(ctx, novel_folder)

        previous_context, continuation_requirement = self._get_previous_context(
            chapters_dir
        )
        characters_digest = self._build_characters_digest(ctx)

        if ending_type:
            unresolved_threads = self._extract_unresolved_threads(memory_content)
            route_info = self._extract_route_scores(ctx)
            final_rounds_ledger = self._build_event_ledger(ctx, compact=False) or "（暂无台账）"
            prompt = NOVEL_ENDING_PROMPT.format(
                novel_title=novel_title,
                characters_digest=characters_digest,
                memory_content=memory_content,
                previous_context=previous_context,
                unresolved_threads=unresolved_threads,
                ending_type=ending_type,
                route_leader=route_info["leader"] or "未明确",
                route_scores=json.dumps(route_info["scores"], ensure_ascii=False),
                final_rounds_ledger=final_rounds_ledger,
            )
            chapter_content = await self.llm_adapter.generate_text(
                ctx=ctx,
                prompt=prompt,
                system_prompt="你是一个专业的小说作家。",
                timeout=600,
                method_name="generate_novel_ending",
            )
            chapter_filename = "ending.md"
        else:
            chapter_event_ledger = self._extract_chapter_events(
                ctx, memory_content, chapter_num, chapter_num
            )
            prompt = NOVEL_CHAPTER_PROMPT.format(
                novel_title=novel_title,
                characters_digest=characters_digest,
                memory_content=memory_content,
                previous_context=previous_context,
                chapter_event_ledger=chapter_event_ledger,
                chapter_num=chapter_num,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                continuation_requirement=continuation_requirement,
            )
            chapter_content = await self.llm_adapter.generate_text(
                ctx=ctx,
                prompt=prompt,
                system_prompt="你是一个专业的小说作家。",
                timeout=600,
                method_name="generate_novel_chapter",
            )
            chapter_filename = f"chapter_{chapter_num:02d}.md"

        if is_current:
            chapter_path = self.novel_repository.save_current_chapter(
                ctx, chapter_filename, chapter_content
            )
            self._merge_current(ctx)
        else:
            chapter_path = self.novel_repository.save_legacy_chapter(
                ctx, novel_folder, chapter_filename, chapter_content
            )

        return {
            "success": True,
            "chapter_num": chapter_num,
            "chapter_path": chapter_path,
            "chapter_content": chapter_content,
        }

    def merge_novel(self, ctx: GameContext, novel_folder: str) -> dict:
        plan_data = self.novel_repository.load_legacy_plan(ctx, novel_folder)
        novel_title = plan_data.get("title", "未命名小说")
        chapter_files = self.novel_repository.list_legacy_chapter_files(ctx, novel_folder)
        if not chapter_files:
            raise Exception(f"没有找到章节文件: {novel_folder}")

        merged_content = f"# {novel_title}\n\n"
        chapters_dir = self.novel_repository.legacy_chapters_dir(ctx, novel_folder)
        for chapter_file in chapter_files:
            chapter_path = os.path.join(chapters_dir, chapter_file)
            merged_content += self.novel_repository.load_text(chapter_path) + "\n\n"

        novel_path = self.novel_repository.save_legacy_merged_novel(
            ctx, novel_folder, merged_content
        )
        return {
            "success": True,
            "novel_path": novel_path,
            "novel_content": merged_content,
            "total_chapters": len(chapter_files),
        }

    def get_novel_status(self, ctx: GameContext, novel_folder: str) -> dict:
        plan_data = self.novel_repository.load_legacy_plan(ctx, novel_folder)
        generated_chapters = len(
            self.novel_repository.list_legacy_chapter_files(ctx, novel_folder)
        )
        total_chapters = plan_data.get("total_chapters", 0)
        return {
            "novel_folder": novel_folder,
            "title": plan_data.get("title", ""),
            "total_chapters": total_chapters,
            "generated_chapters": generated_chapters,
            "progress": generated_chapters / total_chapters if total_chapters > 0 else 0,
            "is_complete": generated_chapters >= total_chapters,
        }
