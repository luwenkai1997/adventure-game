from pydantic import BaseModel, Field
from typing import Optional


class CheckRequest(BaseModel):
    attribute: str
    skill: Optional[str] = ""
    difficulty: int = Field(default=12, ge=1, le=30)
    description: Optional[str] = ""


class CheckResult(BaseModel):
    roll: int
    modifier: int
    skill_bonus: int = 0
    total: int
    difficulty: int
    success: bool
    critical: bool = False
    fumble: bool = False
    narrative: Optional[str] = ""


DIFFICULTY_NAMES = {
    8: "简单",
    12: "普通",
    16: "困难",
    20: "极难",
    25: "几乎不可能",
}

DIFFICULTY_COLORS = {
    8: "#00ff88",
    12: "#00ccff",
    16: "#ffcc00",
    20: "#ff8800",
    25: "#ff4444",
}


def get_difficulty_name(dc: int) -> str:
    if dc <= 8:
        return "简单"
    elif dc <= 12:
        return "普通"
    elif dc <= 16:
        return "困难"
    elif dc <= 20:
        return "极难"
    else:
        return "几乎不可能"


def get_difficulty_color(dc: int) -> str:
    if dc <= 8:
        return "#00ff88"
    elif dc <= 12:
        return "#00ccff"
    elif dc <= 16:
        return "#ffcc00"
    elif dc <= 20:
        return "#ff8800"
    else:
        return "#ff4444"
