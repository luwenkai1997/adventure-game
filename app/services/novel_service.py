import os
import json
from datetime import datetime
from typing import Optional, List
from app.config import (
    NOVEL_GENERATION_PROMPT,
    NOVEL_TITLE_PROMPT,
    NOVEL_CHAPTER_PROMPT,
    NOVEL_ENDING_PROMPT,
    BASE_DIR,
    NOVELS_DIR,
)
from app.utils.file_storage import load_memory
from app.utils.llm_client import call_llm, parse_json_response


class NovelService:
    def __init__(self):
        pass

    def generate_full_novel(self) -> dict:
        memory_content = load_memory()

        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        prompt = NOVEL_GENERATION_PROMPT.format(memory_content=memory_content)

        novel_content = call_llm(prompt, "你是一个专业的小说作家。", timeout=300)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        novel_folder = f"novel-{timestamp}"
        novels_dir = os.path.join(BASE_DIR, 'novels', novel_folder)
        os.makedirs(novels_dir, exist_ok=True)

        novel_path = os.path.join(novels_dir, 'novel.md')
        with open(novel_path, 'w', encoding='utf-8') as f:
            f.write(novel_content)

        return {
            'novel_folder': novel_folder,
            'novel_path': novel_path,
            'novel_content': novel_content
        }

    def plan_novel(self) -> dict:
        memory_content = load_memory()

        if not memory_content:
            raise Exception("memory.md不存在，请先开始游戏")

        prompt = NOVEL_TITLE_PROMPT.format(memory_content=memory_content)

        response = call_llm(prompt, "你是一个专业的小说策划师。", timeout=120)
        plan_data = parse_json_response(response)

        if plan_data is None:
            raise Exception(f"LLM返回了null内容，原始响应: {response[:500]}")
        if not isinstance(plan_data, dict):
            raise Exception(f"LLM返回格式错误：期望JSON对象，实际为{type(plan_data)}，内容: {str(plan_data)[:200]}")
        if 'title' not in plan_data:
            raise Exception(f"LLM返回数据缺少title字段: {str(plan_data)[:200]}")
        if 'chapters' not in plan_data:
            raise Exception(f"LLM返回数据缺少chapters字段: {str(plan_data)[:200]}")
        if not isinstance(plan_data['chapters'], list):
            raise Exception(f"LLM返回数据chapters不是数组: {str(plan_data)[:200]}")
        if len(plan_data['chapters']) == 0:
            raise Exception(f"LLM返回数据chapters为空数组")
        if 'title' not in plan_data['chapters'][0]:
            raise Exception(f"LLM返回数据第一章缺少title字段")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        novel_folder = f"novel-{timestamp}"
        novels_dir = os.path.join(BASE_DIR, 'novels', novel_folder)
        os.makedirs(novels_dir, exist_ok=True)
        chapters_dir = os.path.join(novels_dir, 'chapters')
        os.makedirs(chapters_dir, exist_ok=True)

        plan_path = os.path.join(novels_dir, 'plan.json')
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)

        return {
            'novel_folder': novel_folder,
            'plan': plan_data
        }

    def generate_chapter(
        self,
        novel_folder: str,
        chapter_num: int,
        chapter_title: str,
        chapter_summary: str,
        ending_type: str = ""
    ) -> dict:
        memory_content = load_memory()

        if not memory_content:
            raise Exception("memory.md不存在")

        novels_dir = os.path.join(BASE_DIR, 'novels', novel_folder)
        plan_path = os.path.join(novels_dir, 'plan.json')

        if not os.path.exists(plan_path):
            raise Exception("小说规划不存在，请先规划小说")

        with open(plan_path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        novel_title = plan_data.get('title', '未命名小说')

        chapters_dir = os.path.join(novels_dir, 'chapters')
        previous_chapters = []
        if os.path.exists(chapters_dir):
            for filename in sorted(os.listdir(chapters_dir)):
                if filename.endswith('.md'):
                    with open(os.path.join(chapters_dir, filename), 'r', encoding='utf-8') as f:
                        previous_chapters.append(f.read())

        if previous_chapters:
            last_chapter = previous_chapters[-1]
            if len(last_chapter) > 1000:
                last_chapter_summary = last_chapter[-1000:]
            else:
                last_chapter_summary = last_chapter
            previous_context = f"上一章内容摘要（用于衔接）：\n...{last_chapter_summary}"
            continuation_requirement = "本章开头需要与上一章内容自然衔接"
        else:
            previous_context = "（这是第一章，没有前文）"
            continuation_requirement = "这是开篇章节，需要引人入胜的开头"

        if ending_type:
            prompt = NOVEL_ENDING_PROMPT.format(
                novel_title=novel_title,
                memory_content=memory_content,
                previous_context=previous_context,
                ending_type=ending_type
            )
            chapter_content = call_llm(prompt, "你是一个专业的小说作家。", timeout=180)
            chapter_filename = "ending.md"
        else:
            prompt = NOVEL_CHAPTER_PROMPT.format(
                novel_title=novel_title,
                memory_content=memory_content,
                previous_context=previous_context,
                chapter_num=chapter_num,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                continuation_requirement=continuation_requirement
            )
            chapter_content = call_llm(prompt, "你是一个专业的小说作家。", timeout=180)
            chapter_filename = f"chapter_{chapter_num:02d}.md"

        chapter_path = os.path.join(chapters_dir, chapter_filename)
        with open(chapter_path, 'w', encoding='utf-8') as f:
            f.write(chapter_content)

        return {
            'success': True,
            'chapter_num': chapter_num,
            'chapter_path': chapter_path,
            'chapter_content': chapter_content
        }

    def merge_novel(self, novel_folder: str) -> dict:
        novels_dir = os.path.join(BASE_DIR, 'novels', novel_folder)
        plan_path = os.path.join(novels_dir, 'plan.json')

        if not os.path.exists(plan_path):
            raise Exception("小说规划不存在")

        with open(plan_path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        novel_title = plan_data.get('title', '未命名小说')
        chapters_dir = os.path.join(novels_dir, 'chapters')

        if not os.path.exists(chapters_dir):
            raise Exception("没有找到章节文件")

        chapter_files = sorted([f for f in os.listdir(chapters_dir) if f.endswith('.md')])

        if not chapter_files:
            raise Exception(f"没有找到章节文件。请检查novel_folder是否正确: {novel_folder}，章节目录: {chapters_dir}")

        merged_content = f"# {novel_title}\n\n"

        for chapter_file in chapter_files:
            chapter_path = os.path.join(chapters_dir, chapter_file)
            with open(chapter_path, 'r', encoding='utf-8') as f:
                chapter_content = f.read()
            merged_content += chapter_content + "\n\n"

        novel_path = os.path.join(novels_dir, 'novel.md')
        with open(novel_path, 'w', encoding='utf-8') as nf:
            nf.write(merged_content)

        return {
            'success': True,
            'novel_path': novel_path,
            'novel_content': merged_content,
            'total_chapters': len(chapter_files)
        }

    def get_novel_status(self, novel_folder: str) -> dict:
        novels_dir = os.path.join(BASE_DIR, 'novels', novel_folder)
        plan_path = os.path.join(novels_dir, 'plan.json')

        if not os.path.exists(plan_path):
            raise Exception("小说不存在")

        with open(plan_path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        chapters_dir = os.path.join(novels_dir, 'chapters')
        generated_chapters = 0
        if os.path.exists(chapters_dir):
            generated_chapters = len([f for f in os.listdir(chapters_dir) if f.endswith('.md')])

        total_chapters = plan_data.get('total_chapters', 0)

        return {
            'novel_folder': novel_folder,
            'title': plan_data.get('title', ''),
            'total_chapters': total_chapters,
            'generated_chapters': generated_chapters,
            'progress': generated_chapters / total_chapters if total_chapters > 0 else 0,
            'is_complete': generated_chapters >= total_chapters
        }
