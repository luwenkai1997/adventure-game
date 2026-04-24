"""Achievement system: defines unlockable achievements and evaluates game state against them."""
import json
import logging
import os
from typing import Any, Dict, List, Optional

from app.game_context import GameContext
from app.repositories.base import FileRepositoryPaths
from app.utils.atomic_io import atomic_write_json

logger = logging.getLogger(__name__)

# ─── Achievement Definitions ────────────────────────────────────────────────
# Each entry: id, title, description, icon, condition key (checked by evaluate())
ACHIEVEMENTS: List[Dict[str, Any]] = [
    {
        "id": "first_step",
        "title": "初出茅庐",
        "description": "完成第一个回合",
        "icon": "🌱",
        "secret": False,
    },
    {
        "id": "ten_turns",
        "title": "身经百战",
        "description": "完成 10 个回合",
        "icon": "⚔️",
        "secret": False,
    },
    {
        "id": "check_pass",
        "title": "好运连连",
        "description": "通过第一次检定",
        "icon": "🎲",
        "secret": False,
    },
    {
        "id": "check_10",
        "title": "铁骨铮铮",
        "description": "累计通过 10 次检定",
        "icon": "💪",
        "secret": False,
    },
    {
        "id": "hard_check",
        "title": "以弱胜强",
        "description": "通过难度 18 及以上的检定",
        "icon": "🏆",
        "secret": True,
    },
    {
        "id": "first_objective",
        "title": "言出必行",
        "description": "完成第一个任务目标",
        "icon": "📋",
        "secret": False,
    },
    {
        "id": "five_objectives",
        "title": "使命必达",
        "description": "累计完成 5 个任务目标",
        "icon": "🎯",
        "secret": False,
    },
    {
        "id": "npc_talker",
        "title": "八面玲珑",
        "description": "与 3 个不同 NPC 交谈过",
        "icon": "🗣️",
        "secret": False,
    },
    {
        "id": "item_collector",
        "title": "囤积居奇",
        "description": "物品栏同时持有 5 件物品",
        "icon": "🎒",
        "secret": False,
    },
    {
        "id": "items_10",
        "title": "富甲一方",
        "description": "累计获得 10 件物品",
        "icon": "💎",
        "secret": False,
    },
    {
        "id": "key_decision",
        "title": "命运抉择",
        "description": "做出第一个关键决定",
        "icon": "🔱",
        "secret": False,
    },
    {
        "id": "game_ended",
        "title": "落幕",
        "description": "走向了一个结局",
        "icon": "🌅",
        "secret": False,
    },
]

ACHIEVEMENT_MAP = {a["id"]: a for a in ACHIEVEMENTS}

# ─── Repository helpers ──────────────────────────────────────────────────────

def _default_state() -> Dict[str, Any]:
    return {
        "unlocked": [],
        "stats": {
            "total_turns": 0,
            "checks_passed": 0,
            "max_check_difficulty_passed": 0,
            "npcs_talked_set": [],
            "objectives_completed": 0,
            "items_acquired": 0,
            "key_decisions_made": 0,
            "game_ended": False,
        },
    }


def load_state(paths: FileRepositoryPaths, ctx: GameContext) -> Dict[str, Any]:
    path = paths.achievements_path(ctx)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            # ensure new stat keys exist
            default_stats = _default_state()["stats"]
            for k, v in default_stats.items():
                state.setdefault("stats", {})
                state["stats"].setdefault(k, v)
            return state
        except Exception:
            logger.warning("Failed to load achievements.json, resetting.", exc_info=True)
    return _default_state()


def save_state(paths: FileRepositoryPaths, ctx: GameContext, state: Dict[str, Any]) -> None:
    atomic_write_json(paths.achievements_path(ctx), state)


# ─── Evaluation ─────────────────────────────────────────────────────────────

def evaluate_and_unlock(
    paths: FileRepositoryPaths,
    ctx: GameContext,
    *,
    check_passed: bool = False,
    check_difficulty: int = 0,
    objectives_completed_delta: int = 0,
    inventory_added_delta: int = 0,
    current_inventory_size: int = 0,
    npc_id_talked: Optional[str] = None,
    is_key_decision: bool = False,
    game_ended: bool = False,
) -> List[Dict[str, Any]]:
    """Update cumulative stats and return list of newly unlocked achievements."""
    state = load_state(paths, ctx)
    stats = state["stats"]
    already_unlocked = set(state["unlocked"])
    newly_unlocked: List[Dict[str, Any]] = []

    # Update stats
    stats["total_turns"] += 1
    if check_passed:
        stats["checks_passed"] += 1
        if check_difficulty > stats.get("max_check_difficulty_passed", 0):
            stats["max_check_difficulty_passed"] = check_difficulty
    if objectives_completed_delta > 0:
        stats["objectives_completed"] += objectives_completed_delta
    if inventory_added_delta > 0:
        stats["items_acquired"] += inventory_added_delta
    if npc_id_talked and npc_id_talked not in stats.get("npcs_talked_set", []):
        stats.setdefault("npcs_talked_set", []).append(npc_id_talked)
    if is_key_decision:
        stats["key_decisions_made"] = stats.get("key_decisions_made", 0) + 1
    if game_ended:
        stats["game_ended"] = True

    # Check conditions
    def unlock(aid: str) -> None:
        if aid not in already_unlocked:
            already_unlocked.add(aid)
            state["unlocked"].append(aid)
            if aid in ACHIEVEMENT_MAP:
                newly_unlocked.append(ACHIEVEMENT_MAP[aid])

    if stats["total_turns"] >= 1:
        unlock("first_step")
    if stats["total_turns"] >= 10:
        unlock("ten_turns")
    if stats["checks_passed"] >= 1:
        unlock("check_pass")
    if stats["checks_passed"] >= 10:
        unlock("check_10")
    if stats.get("max_check_difficulty_passed", 0) >= 18:
        unlock("hard_check")
    if stats["objectives_completed"] >= 1:
        unlock("first_objective")
    if stats["objectives_completed"] >= 5:
        unlock("five_objectives")
    if len(stats.get("npcs_talked_set", [])) >= 3:
        unlock("npc_talker")
    if current_inventory_size >= 5:
        unlock("item_collector")
    if stats["items_acquired"] >= 10:
        unlock("items_10")
    if stats.get("key_decisions_made", 0) >= 1:
        unlock("key_decision")
    if stats.get("game_ended"):
        unlock("game_ended")

    save_state(paths, ctx, state)
    return newly_unlocked


def get_achievements_with_status(
    paths: FileRepositoryPaths,
    ctx: GameContext,
) -> List[Dict[str, Any]]:
    """Return all achievements annotated with unlocked status."""
    state = load_state(paths, ctx)
    unlocked = set(state["unlocked"])
    result = []
    for ach in ACHIEVEMENTS:
        entry = dict(ach)
        entry["unlocked"] = ach["id"] in unlocked
        result.append(entry)
    return result
