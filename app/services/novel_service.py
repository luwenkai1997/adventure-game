import os
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


class NovelService:
    def __init__(
        self,
        memory_repository,
        save_repository,
        novel_repository,
        llm_adapter,
    ):
        self.memory_repository = memory_repository
        self.save_repository = save_repository
        self.novel_repository = novel_repository
        self.llm_adapter = llm_adapter

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

    def calculate_chapter_range(self, game_rounds: int = 0) -> tuple:
        effective_rounds = game_rounds or 10
        min_chapters = max(2, int(effective_rounds * 0.35))
        max_chapters = max(min_chapters + 1, int(effective_rounds * 0.50))
        return min(min_chapters, 15), min(max_chapters, 20), effective_rounds

    def get_novel_progress(
        self, ctx: Optional[GameContext], current_round: int = 0
    ) -> Dict[str, Any]:
        state = self._load_state(ctx)
        if current_round <= 0:
            current_round = self.save_repository.get_round_count(ctx)

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

    async def generate_incremental(
        self, ctx: GameContext, ending_type: str = "", current_round: int = 0
    ) -> Dict[str, Any]:
        memory_content = self.memory_repository.load_text(ctx)
        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        if current_round <= 0:
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
        plan_data = await self.llm_adapter.generate_json(
            ctx=ctx,
            prompt=NOVEL_TITLE_PROMPT.format(
                memory_content=memory_content,
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

        min_chapters = min(max(1, int(new_rounds * 0.35)), 8)
        max_chapters = min(max(min_chapters + 1, int(new_rounds * 0.50)), 10)
        start_chapter_num = len(state["chapters"]) + 1

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

        for index, chapter in enumerate(plan_chapters):
            chapter_num = chapter.get("chapter_num", len(state["chapters"]) + 1)
            chapter_title = chapter.get("title", f"第{chapter_num}章")
            chapter_summary = chapter.get("summary", chapter.get("outline", ""))
            previous_context, continuation_requirement = self._get_previous_context(
                chapters_dir
            )

            prompt = NOVEL_CHAPTER_PROMPT.format(
                novel_title=title,
                memory_content=memory_content,
                previous_context=previous_context,
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

                round_start = int(from_round + index * rounds_per_chapter)
                round_end = int(from_round + (index + 1) * rounds_per_chapter - 1)
                if index == total_plan - 1:
                    round_end = to_round

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
            except Exception:
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
        prompt = NOVEL_ENDING_PROMPT.format(
            novel_title=title,
            memory_content=memory_content,
            previous_context=previous_context,
            ending_type=ending_type,
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
        plan_data = await self.llm_adapter.generate_json(
            ctx=ctx,
            prompt=NOVEL_TITLE_PROMPT.format(
                memory_content=memory_content,
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

        if ending_type:
            prompt = NOVEL_ENDING_PROMPT.format(
                novel_title=novel_title,
                memory_content=memory_content,
                previous_context=previous_context,
                ending_type=ending_type,
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
            prompt = NOVEL_CHAPTER_PROMPT.format(
                novel_title=novel_title,
                memory_content=memory_content,
                previous_context=previous_context,
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
