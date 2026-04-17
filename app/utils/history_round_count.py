"""Derive narrative round counts from history snapshots (undo stack is capped)."""

from typing import Any, Dict, List


def count_main_narrative_logs(logs: List[Any]) -> int:
    """Count narrative log entries, excluding omen/route_hint lines."""
    if not logs:
        return 0
    n = 0
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        log_text = entry.get("log") or ""
        if log_text.startswith("\U0001F31F 命运前兆:") or log_text.startswith(
            "\U0001F9ED 路线关注:"
        ):
            continue
        if not log_text:
            continue
        n += 1
    return n


def narrative_round_count_from_history(history: List[Dict[str, Any]]) -> int:
    """Same semantics as file_storage.get_game_round_count but for an explicit history list."""
    if not history:
        return 0
    best = max(history, key=lambda s: len(s.get("logs", [])))
    n = count_main_narrative_logs(best.get("logs", []))
    if n > 0:
        return n
    ch = history[-1].get("chapter")
    if isinstance(ch, int) and ch > 0:
        return ch
    return len(history)
