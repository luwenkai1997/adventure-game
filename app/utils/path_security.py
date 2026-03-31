"""Validate user-supplied path segments to prevent directory traversal."""
import os
import re

from app.errors import AppError

GAME_ID_PATTERN = re.compile(r"^game_[0-9A-Za-z_-]{8,256}$")
CHAR_ID_PATTERN = re.compile(r"^[0-9A-Za-z_-]{1,128}$")
SLOT_ID_PATTERN = re.compile(r"^[0-9A-Za-z_-]{1,32}$")
NOVEL_FOLDER_PATTERN = re.compile(r"^[0-9A-Za-z_.-]{1,128}$")


def _reject_if_unsafe(segment: str, pattern: re.Pattern, field: str) -> str:
    if not segment or not isinstance(segment, str):
        raise AppError("validation_error", f"无效的{field}", status_code=400)
    segment = segment.strip()
    if ".." in segment or "/" in segment or "\\" in segment:
        raise AppError("validation_error", f"{field}包含非法字符", status_code=400)
    if not pattern.fullmatch(segment):
        raise AppError("validation_error", f"{field}格式不正确", status_code=400)
    return segment


def validate_game_id(game_id: str) -> str:
    return _reject_if_unsafe(game_id, GAME_ID_PATTERN, "游戏ID")


def validate_char_id(char_id: str) -> str:
    return _reject_if_unsafe(char_id, CHAR_ID_PATTERN, "角色ID")


def validate_slot_id(slot_id: str) -> str:
    return _reject_if_unsafe(slot_id, SLOT_ID_PATTERN, "存档槽位")


def validate_novel_folder(folder: str) -> str:
    return _reject_if_unsafe(folder, NOVEL_FOLDER_PATTERN, "小说目录名")


def assert_path_under_root(resolved_path: str, root_dir: str) -> None:
    root_real = os.path.realpath(root_dir)
    target_real = os.path.realpath(resolved_path)
    try:
        common = os.path.commonpath([root_real, target_real])
    except ValueError:
        raise AppError("validation_error", "路径越界", status_code=400)
    if os.path.normcase(common) != os.path.normcase(root_real):
        raise AppError("validation_error", "路径越界", status_code=400)
