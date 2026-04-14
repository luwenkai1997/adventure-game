import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)
from app.config import (
    NOVEL_GENERATION_PROMPT,
    NOVEL_TITLE_PROMPT,
    NOVEL_CHAPTER_PROMPT,
    NOVEL_ENDING_PROMPT,
    NOVEL_INCREMENTAL_PLAN_PROMPT,
    BASE_DIR,
)
from app.utils.file_storage import (
    load_memory,
    load_history,
    get_novel_path,
    get_or_create_novels_dir,
    get_game_round_count,
)
from app.services.llm_gateway import call_llm
from app.utils.json_utils import parse_json_response


class NovelService:
    def __init__(self):
        pass

    # ── helpers ──────────────────────────────────────────────

    def _current_novel_dir(self) -> str:
        """Return the path to the 'current' novel directory for this game."""
        novels_dir = get_or_create_novels_dir()
        current_dir = os.path.join(novels_dir, "current")
        os.makedirs(current_dir, exist_ok=True)
        chapters_dir = os.path.join(current_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        return current_dir

    def _state_path(self) -> str:
        return os.path.join(self._current_novel_dir(), "novel_state.json")

    def _load_state(self) -> Optional[Dict[str, Any]]:
        path = self._state_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_state(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = datetime.now().isoformat()
        with open(self._state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _init_state(self, title: str) -> Dict[str, Any]:
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
        self._save_state(state)
        return state

    def _existing_chapters_summary(self, state: Dict[str, Any]) -> str:
        """Build a concise summary of existing chapters for the incremental prompt."""
        if not state["chapters"]:
            return "（无已有章节）"
        lines = []
        for ch in state["chapters"]:
            rounds = ch.get("covers_rounds", [])
            rounds_str = f"（覆盖第{rounds[0]}-{rounds[1]}轮）" if len(rounds) == 2 else ""
            lines.append(f"- 第{ch['chapter_num']}章《{ch['title']}》{rounds_str}：{ch.get('summary', '')}")
        return "\n".join(lines)

    # ── chapter range calculation ────────────────────────────

    def calculate_chapter_range(self, game_rounds: int = 0) -> tuple:
        if game_rounds == 0:
            history = load_history()
            game_rounds = len(history) or 10

        min_chapters = max(2, int(game_rounds * 0.35))
        max_chapters = max(min_chapters + 1, int(game_rounds * 0.50))

        min_chapters = min(min_chapters, 15)
        max_chapters = min(max_chapters, 20)

        return min_chapters, max_chapters, game_rounds

    # ── incremental generation (main entry) ──────────────────

    def get_novel_progress(self, current_round: int = 0) -> Dict[str, Any]:
        """Return current novel progress information for the frontend."""
        state = self._load_state()
        if current_round <= 0:
            current_round = get_game_round_count()

        if state is None:
            return {
                "has_novel": False,
                "title": None,
                "chapters_count": 0,
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
            "last_covered_round": state.get("last_covered_round", 0),
            "current_round": current_round,
            "new_rounds": new_rounds,
            "can_continue": new_rounds > 0,
            "status": state.get("status", "in_progress"),
        }

    def get_novel_content(self) -> Dict[str, Any]:
        """Return the merged novel content if it exists."""
        novel_dir = self._current_novel_dir()
        novel_path = os.path.join(novel_dir, "novel.md")
        state = self._load_state()

        if not os.path.exists(novel_path) or state is None:
            return {"has_novel": False, "content": "", "title": ""}

        with open(novel_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "has_novel": True,
            "content": content,
            "title": state.get("title", ""),
            "chapters_count": len(state.get("chapters", [])),
            "status": state.get("status", "in_progress"),
        }

    async def generate_incremental(self, ending_type: str = "", current_round: int = 0) -> Dict[str, Any]:
        """
        Main entry: decide whether to create a fresh novel or continue an existing one.
        If ending_type is provided, also append an ending chapter.
        Returns a streaming-friendly result dict with plan + chapter results.
        """
        memory_content = load_memory()
        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        if current_round <= 0:
            current_round = get_game_round_count()
        if current_round <= 0:
            current_round = 1

        state = self._load_state()

        if state is None:
            # ── First-time: full plan ──
            result = await self._generate_fresh(memory_content, current_round, ending_type)
        else:
            last_covered = state.get("last_covered_round", 0)
            if current_round <= last_covered and not ending_type:
                # Nothing new to write
                merged = self._merge_current()
                return {
                    "success": True,
                    "mode": "no_change",
                    "message": f"没有新剧情需要续写（已覆盖到第{last_covered}轮）",
                    "novel_content": merged["novel_content"],
                    "title": state.get("title", ""),
                    "total_chapters": len(state.get("chapters", [])),
                }
            # ── Incremental continuation ──
            result = await self._generate_continuation(
                state, memory_content, current_round, ending_type
            )

        return result

    # ── fresh generation ─────────────────────────────────────

    async def _generate_fresh(
        self, memory_content: str, current_round: int, ending_type: str = ""
    ) -> Dict[str, Any]:
        min_ch, max_ch, game_rounds = self.calculate_chapter_range(current_round)

        prompt = NOVEL_TITLE_PROMPT.format(
            memory_content=memory_content,
            min_chapters=min_ch,
            max_chapters=max_ch,
        )
        response = await call_llm(prompt, "你是一个专业的小说策划师。", timeout=600)
        plan_data = parse_json_response(response)
        self._validate_plan(plan_data)

        title = plan_data["title"]
        state = self._init_state(title)
        state["total_game_rounds"] = current_round

        # Save plan.json for reference
        plan_path = os.path.join(self._current_novel_dir(), "plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)

        # Generate each chapter
        chapters_generated = await self._generate_chapters_from_plan(
            plan_data["chapters"], title, memory_content, state, 1, current_round
        )

        # Ending chapter if requested
        if ending_type:
            await self._append_ending(state, title, memory_content, ending_type)

        merged = self._merge_current()

        return {
            "success": True,
            "mode": "fresh",
            "title": title,
            "total_chapters": len(state["chapters"]),
            "novel_content": merged["novel_content"],
            "chapters_generated": chapters_generated,
        }

    # ── incremental continuation ─────────────────────────────

    async def _generate_continuation(
        self,
        state: Dict[str, Any],
        memory_content: str,
        current_round: int,
        ending_type: str = "",
    ) -> Dict[str, Any]:
        last_covered = state.get("last_covered_round", 0)
        new_rounds = current_round - last_covered
        title = state.get("title", "未命名小说")

        # Calculate how many chapters for the new content
        min_ch = max(1, int(new_rounds * 0.35))
        max_ch = max(min_ch + 1, int(new_rounds * 0.50))
        min_ch = min(min_ch, 8)
        max_ch = min(max_ch, 10)

        start_num = len(state["chapters"]) + 1

        # Build incremental plan prompt
        prompt = NOVEL_INCREMENTAL_PLAN_PROMPT.format(
            novel_title=title,
            existing_chapters_count=len(state["chapters"]),
            last_covered_round=last_covered,
            existing_chapters_summary=self._existing_chapters_summary(state),
            memory_content=memory_content,
            current_round=current_round,
            min_chapters=min_ch,
            max_chapters=max_ch,
            start_chapter_num=start_num,
        )

        response = await call_llm(prompt, "你是一个专业的小说策划师。", timeout=600)
        plan_data = parse_json_response(response)

        if not plan_data or "chapters" not in plan_data or not plan_data["chapters"]:
            raise Exception("续写规划失败：LLM返回数据缺少chapters字段")

        state["total_game_rounds"] = current_round

        chapters_generated = await self._generate_chapters_from_plan(
            plan_data["chapters"],
            title,
            memory_content,
            state,
            last_covered + 1,
            current_round,
        )

        if ending_type:
            await self._append_ending(state, title, memory_content, ending_type)

        merged = self._merge_current()

        return {
            "success": True,
            "mode": "continuation",
            "title": title,
            "total_chapters": len(state["chapters"]),
            "new_chapters": chapters_generated,
            "novel_content": merged["novel_content"],
        }

    # ── shared chapter generation ────────────────────────────

    async def _generate_chapters_from_plan(
        self,
        plan_chapters: List[Dict],
        title: str,
        memory_content: str,
        state: Dict[str, Any],
        from_round: int,
        to_round: int,
    ) -> int:
        """Generate chapters from a plan and update state. Returns count generated."""
        novel_dir = self._current_novel_dir()
        chapters_dir = os.path.join(novel_dir, "chapters")
        generated = 0

        total_plan = len(plan_chapters)
        rounds_per_chapter = max(1, (to_round - from_round + 1) / total_plan) if total_plan > 0 else 1

        for i, ch in enumerate(plan_chapters):
            chapter_num = ch.get("chapter_num", len(state["chapters"]) + 1)
            chapter_title = ch.get("title", f"第{chapter_num}章")
            chapter_summary = ch.get("summary", ch.get("outline", ""))

            # Build previous context from the last generated chapter
            previous_context, continuation_req = self._get_previous_context(chapters_dir)

            prompt = NOVEL_CHAPTER_PROMPT.format(
                novel_title=title,
                memory_content=memory_content,
                previous_context=previous_context,
                chapter_num=chapter_num,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                continuation_requirement=continuation_req,
            )

            try:
                content = await call_llm(prompt, "你是一个专业的小说作家。", timeout=600)
                filename = f"chapter_{chapter_num:02d}.md"
                filepath = os.path.join(chapters_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

                # Calculate which rounds this chapter covers
                round_start = int(from_round + i * rounds_per_chapter)
                round_end = int(from_round + (i + 1) * rounds_per_chapter - 1)
                if i == total_plan - 1:
                    round_end = to_round  # last chapter covers everything remaining

                state["chapters"].append({
                    "chapter_num": chapter_num,
                    "title": chapter_title,
                    "summary": chapter_summary,
                    "covers_rounds": [round_start, round_end],
                    "generated_at": datetime.now().isoformat(),
                    "file": filename,
                })
                state["last_covered_round"] = to_round
                self._save_state(state)
                generated += 1
            except Exception as e:
                logger.error(f"第{chapter_num}章生成失败: {e}")
                continue

        return generated

    async def _append_ending(
        self,
        state: Dict[str, Any],
        title: str,
        memory_content: str,
        ending_type: str,
    ) -> None:
        """Append an ending chapter."""
        novel_dir = self._current_novel_dir()
        chapters_dir = os.path.join(novel_dir, "chapters")
        previous_context, _ = self._get_previous_context(chapters_dir)

        prompt = NOVEL_ENDING_PROMPT.format(
            novel_title=title,
            memory_content=memory_content,
            previous_context=previous_context,
            ending_type=ending_type,
        )
        content = await call_llm(prompt, "你是一个专业的小说作家。", timeout=600)

        filepath = os.path.join(chapters_dir, "ending.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        state["ending_chapter"] = {
            "title": "终章",
            "ending_type": ending_type,
            "generated_at": datetime.now().isoformat(),
            "file": "ending.md",
        }
        state["status"] = "completed"
        self._save_state(state)

    def _get_previous_context(self, chapters_dir: str) -> tuple:
        """Get the tail of the last chapter for continuation context."""
        if not os.path.exists(chapters_dir):
            return "（这是第一章，没有前文）", "这是开篇章节，需要引人入胜的开头"

        files = sorted(f for f in os.listdir(chapters_dir) if f.endswith(".md"))
        if not files:
            return "（这是第一章，没有前文）", "这是开篇章节，需要引人入胜的开头"

        last_file = os.path.join(chapters_dir, files[-1])
        with open(last_file, "r", encoding="utf-8") as f:
            last_content = f.read()
        tail = last_content[-1000:] if len(last_content) > 1000 else last_content
        return (
            f"上一章内容摘要（用于衔接）：\n...{tail}",
            "本章开头需要与上一章内容自然衔接",
        )

    # ── merge ────────────────────────────────────────────────

    def _merge_current(self) -> Dict[str, Any]:
        """Merge all chapters in the current novel into novel.md."""
        novel_dir = self._current_novel_dir()
        chapters_dir = os.path.join(novel_dir, "chapters")
        state = self._load_state()
        title = state.get("title", "未命名小说") if state else "未命名小说"

        chapter_files = sorted(f for f in os.listdir(chapters_dir) if f.endswith(".md"))
        if not chapter_files:
            return {"novel_content": "", "total_chapters": 0}

        merged = f"# {title}\n\n"
        for cf in chapter_files:
            with open(os.path.join(chapters_dir, cf), "r", encoding="utf-8") as f:
                merged += f.read() + "\n\n"

        novel_path = os.path.join(novel_dir, "novel.md")
        with open(novel_path, "w", encoding="utf-8") as f:
            f.write(merged)

        return {
            "novel_content": merged,
            "total_chapters": len(chapter_files),
            "novel_path": novel_path,
        }

    # ── validation ───────────────────────────────────────────

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

    # ══════════════════════════════════════════════════════════
    # Legacy methods (kept for backward compatibility)
    # ══════════════════════════════════════════════════════════

    async def generate_full_novel(self) -> dict:
        memory_content = load_memory()
        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        prompt = NOVEL_GENERATION_PROMPT.format(
            memory_content=memory_content,
            min_chapters=3,
            max_chapters=15,
        )
        novel_content = await call_llm(prompt, "你是一个专业的小说作家。", timeout=600)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        novel_folder = f"novel-{timestamp}"
        novels_dir = get_novel_path(novel_folder)
        os.makedirs(novels_dir, exist_ok=True)

        novel_path = os.path.join(novels_dir, "novel.md")
        with open(novel_path, "w", encoding="utf-8") as f:
            f.write(novel_content)

        return {
            "novel_folder": novel_folder,
            "novel_path": novel_path,
            "novel_content": novel_content,
        }

    async def plan_novel(self) -> dict:
        memory_content = load_memory()
        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        min_chapters, max_chapters, game_rounds = self.calculate_chapter_range()

        prompt = NOVEL_TITLE_PROMPT.format(
            memory_content=memory_content,
            min_chapters=min_chapters,
            max_chapters=max_chapters,
        )
        response = await call_llm(prompt, "你是一个专业的小说策划师。", timeout=600)
        plan_data = parse_json_response(response)
        self._validate_plan(plan_data)

        plan_data["game_rounds"] = game_rounds
        plan_data["chapter_range"] = {"min": min_chapters, "max": max_chapters}

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        novel_folder = f"novel-{timestamp}"
        novels_dir = get_novel_path(novel_folder)
        os.makedirs(novels_dir, exist_ok=True)
        chapters_dir = os.path.join(novels_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)

        plan_path = os.path.join(novels_dir, "plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)

        return {
            "novel_folder": novel_folder,
            "plan": plan_data,
            "game_rounds": game_rounds,
            "chapter_range": {"min": min_chapters, "max": max_chapters},
        }

    async def generate_chapter(
        self,
        novel_folder: str,
        chapter_num: int,
        chapter_title: str,
        chapter_summary: str,
        ending_type: str = "",
    ) -> dict:
        memory_content = load_memory()
        if not memory_content:
            raise Exception("memory.md不存在")

        novels_dir = get_novel_path(novel_folder)
        plan_path = os.path.join(novels_dir, "plan.json")
        if not os.path.exists(plan_path):
            raise Exception("小说规划不存在，请先规划小说")

        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)

        novel_title = plan_data.get("title", "未命名小说")
        chapters_dir = os.path.join(novels_dir, "chapters")

        previous_context, continuation_req = self._get_previous_context(chapters_dir)

        if ending_type:
            prompt = NOVEL_ENDING_PROMPT.format(
                novel_title=novel_title,
                memory_content=memory_content,
                previous_context=previous_context,
                ending_type=ending_type,
            )
            chapter_content = await call_llm(prompt, "你是一个专业的小说作家。", timeout=600)
            chapter_filename = "ending.md"
        else:
            prompt = NOVEL_CHAPTER_PROMPT.format(
                novel_title=novel_title,
                memory_content=memory_content,
                previous_context=previous_context,
                chapter_num=chapter_num,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                continuation_requirement=continuation_req,
            )
            chapter_content = await call_llm(prompt, "你是一个专业的小说作家。", timeout=600)
            chapter_filename = f"chapter_{chapter_num:02d}.md"

        os.makedirs(chapters_dir, exist_ok=True)
        chapter_path = os.path.join(chapters_dir, chapter_filename)
        with open(chapter_path, "w", encoding="utf-8") as f:
            f.write(chapter_content)

        return {
            "success": True,
            "chapter_num": chapter_num,
            "chapter_path": chapter_path,
            "chapter_content": chapter_content,
        }

    def merge_novel(self, novel_folder: str) -> dict:
        novels_dir = get_novel_path(novel_folder)
        plan_path = os.path.join(novels_dir, "plan.json")
        if not os.path.exists(plan_path):
            raise Exception("小说规划不存在")

        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)

        novel_title = plan_data.get("title", "未命名小说")
        chapters_dir = os.path.join(novels_dir, "chapters")

        if not os.path.exists(chapters_dir):
            raise Exception("没有找到章节文件")

        chapter_files = sorted(f for f in os.listdir(chapters_dir) if f.endswith(".md"))
        if not chapter_files:
            raise Exception(f"没有找到章节文件: {novel_folder}")

        merged_content = f"# {novel_title}\n\n"
        for chapter_file in chapter_files:
            chapter_path = os.path.join(chapters_dir, chapter_file)
            with open(chapter_path, "r", encoding="utf-8") as f:
                merged_content += f.read() + "\n\n"

        novel_path = os.path.join(novels_dir, "novel.md")
        with open(novel_path, "w", encoding="utf-8") as nf:
            nf.write(merged_content)

        return {
            "success": True,
            "novel_path": novel_path,
            "novel_content": merged_content,
            "total_chapters": len(chapter_files),
        }

    def get_novel_status(self, novel_folder: str) -> dict:
        novels_dir = get_novel_path(novel_folder)
        plan_path = os.path.join(novels_dir, "plan.json")
        if not os.path.exists(plan_path):
            raise Exception("小说不存在")

        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)

        chapters_dir = os.path.join(novels_dir, "chapters")
        generated_chapters = 0
        if os.path.exists(chapters_dir):
            generated_chapters = len([f for f in os.listdir(chapters_dir) if f.endswith(".md")])

        total_chapters = plan_data.get("total_chapters", 0)

        return {
            "novel_folder": novel_folder,
            "title": plan_data.get("title", ""),
            "total_chapters": total_chapters,
            "generated_chapters": generated_chapters,
            "progress": generated_chapters / total_chapters if total_chapters > 0 else 0,
            "is_complete": generated_chapters >= total_chapters,
        }
