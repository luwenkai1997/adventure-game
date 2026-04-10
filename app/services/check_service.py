import random
from typing import Optional
from app.game_context import GameContext
from app.models.check import (
    CheckRequest,
    CheckResult,
    get_difficulty_name,
)


class CheckService:
    def __init__(self, player_repository, player_service):
        self.player_repository = player_repository
        self.player_service = player_service

    def roll_d20(self) -> int:
        return random.randint(1, 20)

    def calculate_modifier(self, attribute: int) -> int:
        return (attribute - 10) // 2

    def get_attribute_value(self, ctx: Optional[GameContext], attribute: str) -> int:
        player = self.player_repository.load(ctx)
        if not player:
            return 10

        attr_map = {
            "strength": "strength",
            "dexterity": "dexterity",
            "constitution": "constitution",
            "intelligence": "intelligence",
            "wisdom": "wisdom",
            "charisma": "charisma",
            "str": "strength",
            "dex": "dexterity",
            "con": "constitution",
            "int": "intelligence",
            "wis": "wisdom",
            "cha": "charisma",
        }

        attr_key = attr_map.get(attribute.lower(), attribute)
        return player.get(attr_key, 10)

    def get_skill_level(self, ctx: Optional[GameContext], skill_name: str) -> int:
        player = self.player_repository.load(ctx)
        if not player or not player.get("skills"):
            return 0

        for skill in player["skills"]:
            if skill.get("name") == skill_name:
                return skill.get("level", 0)

        return 0

    def perform_check(self, ctx: Optional[GameContext], request: CheckRequest) -> CheckResult:
        roll = self.roll_d20()
        attribute_value = self.get_attribute_value(ctx, request.attribute)
        modifier = self.calculate_modifier(attribute_value)
        skill_bonus = 0

        if request.skill:
            skill_bonus = self.get_skill_level(ctx, request.skill)

        total = roll + modifier + skill_bonus
        difficulty = request.difficulty

        critical = roll == 20
        fumble = roll == 1
        success = (total >= difficulty) or critical

        if fumble:
            success = False
        elif critical:
            success = True

        narrative = self._generate_narrative(
            roll,
            modifier,
            skill_bonus,
            total,
            difficulty,
            success,
            critical,
            fumble,
            request.description or "",
        )

        growth_summary = {}
        if request.skill:
            growth_summary["skill_growth"] = self.player_service.apply_check_growth(
                ctx, request.skill, success, critical, fumble
            )
            
        hp_effect = self.player_service.apply_hp_effect_from_check(
            ctx, success, critical, fumble
        )
        if hp_effect:
            growth_summary["hp_effect"] = hp_effect

        return CheckResult(
            roll=roll,
            modifier=modifier,
            skill_bonus=skill_bonus,
            total=total,
            difficulty=difficulty,
            success=success,
            critical=critical,
            fumble=fumble,
            narrative=narrative,
            growth=growth_summary
        )

    def _generate_narrative(
        self,
        roll: int,
        modifier: int,
        skill_bonus: int,
        total: int,
        difficulty: int,
        success: bool,
        critical: bool,
        fumble: bool,
        description: str = "",
    ) -> str:
        if critical:
            if description:
                return f"完美！你投出了20点，加上修正值{total - roll}，总计{total}点。{description}——你的表现堪称完美！"
            return f"大成功！你投出了20点（自然大成功！），加上修正值{total - roll}，总计{total}点，远超难度{difficulty}！"

        if fumble:
            if description:
                return f"糟糕！你投出了1点（自然大失败），总计{total}点。{description}——最坏的情况发生了..."
            return f"大失败！你投出了1点（自然大失败），总计{total}点，低于难度{difficulty}。事情完全失控了..."

        if success:
            if description:
                return f"成功！你投出了{roll}点，加上修正值{total - roll}，总计{total}点。{description}"
            return f"成功！投出{roll}点，加上修正值{total - roll}，总计{total}点，超过难度{difficulty}（{get_difficulty_name(difficulty)}）。"

        if description:
            return f"失败。你投出了{roll}点，加上修正值{total - roll}，总计{total}点。{description}——未能成功。"
        return f"失败。投出{roll}点，加上修正值{total - roll}，总计{total}点，未达到难度{difficulty}（{get_difficulty_name(difficulty)}）。"

    def perform_simple_check(
        self, ctx: Optional[GameContext], attribute: str, difficulty: int = 12
    ) -> CheckResult:
        request = CheckRequest(attribute=attribute, difficulty=difficulty)
        return self.perform_check(ctx, request)

    def get_player_check_info(self, ctx: Optional[GameContext]) -> dict:
        player = self.player_repository.load(ctx)
        if not player:
            return {}

        attributes = {}
        for attr_key in [
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ]:
            value = player.get(attr_key, 10)
            modifier = self.calculate_modifier(value)
            attributes[attr_key] = {"value": value, "modifier": modifier}

        return {
            "attributes": attributes,
            "skills": player.get("skills", []),
            "max_hp": player.get("max_hp", 10),
            "current_hp": player.get("current_hp", 10),
        }
