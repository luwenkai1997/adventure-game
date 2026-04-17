"""Utility helpers for maintaining memory.md integrity.

The '## 故事流程' section is the authoritative ledger of game rounds inside
memory.md.  Because the LLM sometimes compresses or omits older rounds when
rewriting memory, this module provides a code-level safety net that appends
any missing round entries *after* the LLM returns its updated text.
"""

import re
from typing import Optional


# Maximum length for the one-line scene summary embedded in the story-flow line.
_SCENE_SUMMARY_MAX = 60

# Header used to locate the story-flow section.
_SECTION_HEADER = "## 故事流程"


def _one_line(text: str, max_len: int = _SCENE_SUMMARY_MAX) -> str:
    """Return the first sentence of *text*, truncated to *max_len* chars."""
    if not text:
        return ""
    # Take up to the first sentence-ending punctuation or newline.
    for sep in ("。", "！", "？", "\n", ".", "!", "?"):
        idx = text.find(sep)
        if idx != -1 and idx < max_len:
            return text[: idx + 1].strip()
    return text[:max_len].strip()


def _parse_existing_rounds(flow_lines: list[str]) -> set[int]:
    """Extract all round numbers already mentioned in the story-flow lines."""
    pattern = re.compile(r"第\s*(\d+)")
    found: set[int] = set()
    for line in flow_lines:
        for m in pattern.finditer(line):
            found.add(int(m.group(1)))
    return found


def ensure_story_flow_round_present(
    memory_md: str,
    round_num: int,
    scene: str,
    selected_choice: str,
    log_summary: str,
) -> str:
    """Guarantee that *round_num* appears in the '## 故事流程' section.

    If the LLM already wrote an entry for *round_num*, this is a no-op.
    Otherwise, a canonical one-liner is appended at the end of the section.

    Args:
        memory_md: Full text content of memory.md (post-LLM rewrite).
        round_num: The game round number that must appear.
        scene:     Scene description for that round (may be long).
        selected_choice: The player's chosen action.
        log_summary: Short narrative log produced by the LLM for that round.

    Returns:
        Updated memory_md string (may be identical to input if already present).
    """
    if not memory_md:
        memory_md = ""

    lines = memory_md.splitlines()

    # Locate the story-flow section boundaries.
    section_start: Optional[int] = None  # index of the "## 故事流程" line
    section_end: Optional[int] = None    # first "## " header after the section

    for i, line in enumerate(lines):
        if line.strip() == _SECTION_HEADER:
            section_start = i
        elif section_start is not None and line.startswith("## ") and i > section_start:
            section_end = i
            break

    flow_lines: list[str] = []
    if section_start is not None:
        end = section_end if section_end is not None else len(lines)
        flow_lines = lines[section_start + 1 : end]

    existing_rounds = _parse_existing_rounds(flow_lines)

    if round_num in existing_rounds:
        # Already present — nothing to do.
        return memory_md

    # Build the canonical entry line.
    scene_short = _one_line(scene)
    choice_short = (selected_choice or "")[:80].replace("\n", " ")
    log_short = (log_summary or "")[:80].replace("\n", " ")
    new_line = f"第{round_num}轮：{scene_short} → 玩家选择「{choice_short}」→ {log_short}"

    if section_start is None:
        # Create the section from scratch before the first "## " we can find
        # that isn't already the story-flow header, or at the end of the file.
        insert_at = len(lines)
        for i, line in enumerate(lines):
            if line.startswith("## ") and "故事流程" not in line:
                insert_at = i
                break
        lines.insert(insert_at, "")
        lines.insert(insert_at + 1, _SECTION_HEADER)
        lines.insert(insert_at + 2, new_line)
    else:
        # Append at end of the story-flow section (just before next header or EOF).
        insert_at = section_end if section_end is not None else len(lines)
        # Walk backwards to skip blank lines so the new line is adjacent to content.
        while insert_at > section_start + 1 and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, new_line)

    return "\n".join(lines)
