import logging
import random
import uuid
from datetime import datetime
from typing import List, Optional

from app.game_context import GameContext
from app.models.player import (
    ATTRIBUTE_NAMES_EN,
    LEGACY_SKILL_INDEX,
    PlayerCharacter,
    PlayerCreateRequest,
    PlayerRandomRequest,
    PlayerSkill,
    get_preset_skills_for_scenario,
)
from app.prompts.scenario_prompts import build_player_generation_prompt
from app.scenarios import (
    DEFAULT_SCENARIO_TYPE,
    get_scenario_profile,
    normalize_scenario_type,
)


logger = logging.getLogger(__name__)


class PlayerService:
    def __init__(self, player_repository, llm_adapter, game_repository):
        self.player_repository = player_repository
        self.llm_adapter = llm_adapter
        self.game_repository = game_repository

    def calculate_modifier(self, attribute: int) -> int:
        return (attribute - 10) // 2

    def calculate_max_hp(self, constitution: int) -> int:
        modifier = self.calculate_modifier(constitution)
        return 10 + modifier * 2

    def _resolve_scenario_type(
        self, ctx: Optional[GameContext], requested: Optional[str] = None
    ) -> str:
        if requested:
            return normalize_scenario_type(requested)
        if ctx is not None:
            game_info = self.game_repository.get_game_info(ctx.game_id) or {}
            return normalize_scenario_type(game_info.get("scenario_type"))
        return DEFAULT_SCENARIO_TYPE

    def _build_skill(self, name: str, scenario_type: str) -> Optional[PlayerSkill]:
        skills_map = get_preset_skills_for_scenario(scenario_type)
        for category, skills in skills_map.items():
            for skill_data in skills:
                if skill_data["name"] == name:
                    return PlayerSkill(
                        id=f"skill_{uuid.uuid4().hex[:6]}",
                        name=skill_data["name"],
                        category=category,
                        level=1,
                        description=skill_data["description"],
                        related_attribute=skill_data["related_attribute"],
                    )
        skill_info = LEGACY_SKILL_INDEX.get(name)
        if skill_info:
            return PlayerSkill(
                id=f"skill_{uuid.uuid4().hex[:6]}",
                name=name,
                category=skill_info["category"],
                level=1,
                description=skill_info["description"],
                related_attribute=skill_info["related_attribute"],
            )
        return None

    def create_player(self, ctx: GameContext, request: PlayerCreateRequest) -> PlayerCharacter:
        scenario_type = self._resolve_scenario_type(ctx, request.scenario_type)
        skills = []
        for skill_name in request.skills:
            skill = self._build_skill(skill_name, scenario_type)
            if skill:
                skills.append(skill)

        max_hp = self.calculate_max_hp(request.constitution)
        player = PlayerCharacter(
            id="player",
            name=request.name,
            age=request.age,
            gender=request.gender,
            race=request.race,
            title=request.title,
            background=request.background,
            appearance=request.appearance,
            personality=request.personality,
            scenario_type=scenario_type,
            strength=request.strength,
            dexterity=request.dexterity,
            constitution=request.constitution,
            intelligence=request.intelligence,
            wisdom=request.wisdom,
            charisma=request.charisma,
            max_hp=max_hp,
            current_hp=max_hp,
            skills=skills,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        self.player_repository.save(ctx, player.model_dump())
        return player

    def random_player(
        self, ctx: GameContext, request: Optional[PlayerRandomRequest] = None
    ) -> PlayerCharacter:
        scenario_type = self._resolve_scenario_type(ctx, request.scenario_type if request else None)
        profile = get_scenario_profile(scenario_type)

        gender_options = ["男", "女", "其他"]
        gender = request.gender if request and request.gender else random.choice(gender_options)
        race = random.choice(profile.player_races)

        attributes = {
            "strength": random.randint(8, 15),
            "dexterity": random.randint(8, 15),
            "constitution": random.randint(8, 15),
            "intelligence": random.randint(8, 15),
            "wisdom": random.randint(8, 15),
            "charisma": random.randint(8, 15),
        }
        used_points = sum(attributes.values())
        points_pool = 90 - used_points
        while points_pool > 0 and used_points < 95:
            attr_to_boost = random.choice(list(attributes.keys()))
            if attributes[attr_to_boost] < 18:
                attributes[attr_to_boost] += 1
                points_pool -= 1

        skills_map = get_preset_skills_for_scenario(scenario_type)
        num_categories = random.randint(2, min(3, len(skills_map)))
        selected_categories = random.sample(list(skills_map.keys()), num_categories)
        skills: List[PlayerSkill] = []
        for category in selected_categories:
            selected_skill = random.choice(skills_map[category])
            skills.append(
                PlayerSkill(
                    id=f"skill_{uuid.uuid4().hex[:6]}",
                    name=selected_skill["name"],
                    category=category,
                    level=random.randint(1, 3),
                    description=selected_skill["description"],
                    related_attribute=selected_skill["related_attribute"],
                )
            )

        name = random.choice(profile.random_names.get(gender, profile.random_names["男"]))
        age = random.randint(18, 40)
        background = random.choice(profile.random_backgrounds)
        appearance = profile.random_appearances.get(race, next(iter(profile.random_appearances.values())))
        title = "江湖行者" if scenario_type == "jianghu" else "流亡者"
        personality = "谨慎、顽强、能在压力中做选择"
        max_hp = self.calculate_max_hp(attributes["constitution"])

        player = PlayerCharacter(
            id="player",
            name=name,
            age=age,
            gender=gender,
            race=race,
            title=title,
            background=background,
            appearance=appearance,
            personality=personality,
            scenario_type=scenario_type,
            strength=attributes["strength"],
            dexterity=attributes["dexterity"],
            constitution=attributes["constitution"],
            intelligence=attributes["intelligence"],
            wisdom=attributes["wisdom"],
            charisma=attributes["charisma"],
            max_hp=max_hp,
            current_hp=max_hp,
            skills=skills,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        self.player_repository.save(ctx, player.model_dump())
        return player

    def get_player(self, ctx: Optional[GameContext]) -> Optional[PlayerCharacter]:
        player_data = self.player_repository.load(ctx)
        if player_data:
            return PlayerCharacter(**player_data)
        return None

    def update_player(self, ctx: Optional[GameContext], updates: dict) -> Optional[PlayerCharacter]:
        player_data = self.player_repository.load(ctx)
        if not player_data:
            return None

        scenario_type = self._resolve_scenario_type(ctx, updates.get("scenario_type") or player_data.get("scenario_type"))
        updates["scenario_type"] = scenario_type

        if "skills" in updates and isinstance(updates["skills"], list):
            processed_skills = []
            existing_skills = player_data.get("skills", [])
            for skill_update in updates["skills"]:
                if isinstance(skill_update, dict):
                    processed_skills.append(
                        self._normalize_skill_payload(
                            skill_update,
                            scenario_type,
                            existing_skills=existing_skills,
                        )
                    )
                else:
                    processed_skills.append(skill_update)
            updates["skills"] = processed_skills

        player_data.update(updates)
        player_data["updated_at"] = datetime.now().isoformat()

        if "constitution" in updates:
            player_data["max_hp"] = self.calculate_max_hp(updates["constitution"])
            if "current_hp" not in updates:
                player_data["current_hp"] = player_data["max_hp"]

        self.player_repository.save(ctx, player_data)
        return PlayerCharacter(**player_data)

    def add_skill(self, ctx: Optional[GameContext], skill_name: str) -> Optional[PlayerCharacter]:
        player = self.get_player(ctx)
        if not player:
            return None
        skill = self._build_skill(skill_name, player.scenario_type)
        if not skill:
            return None
        for existing_skill in player.skills:
            if existing_skill.name == skill_name:
                return player
        player.skills.append(skill)
        return self.update_player(ctx, {"skills": [s.model_dump() for s in player.skills]})

    def remove_skill(self, ctx: Optional[GameContext], skill_name: str) -> Optional[PlayerCharacter]:
        player = self.get_player(ctx)
        if not player:
            return None
        player.skills = [s for s in player.skills if s.name != skill_name]
        return self.update_player(ctx, {"skills": [s.model_dump() for s in player.skills]})

    def update_hp(self, ctx: Optional[GameContext], delta: int) -> Optional[PlayerCharacter]:
        player = self.get_player(ctx)
        if not player:
            return None
        new_hp = max(0, min(player.current_hp + delta, player.max_hp))
        return self.update_player(ctx, {"current_hp": new_hp})

    def apply_check_growth(
        self,
        ctx: Optional[GameContext],
        skill_name: str,
        success: bool,
        critical: bool,
        fumble: bool,
    ) -> dict:
        if not skill_name:
            return {}
        player = self.get_player(ctx)
        if not player:
            return {}

        if critical:
            exp_gain = 20
        elif success:
            exp_gain = 10
        elif fumble:
            exp_gain = 0
        else:
            exp_gain = 5

        if exp_gain == 0:
            return {"skill": skill_name, "exp_gained": 0, "leveled_up": False}

        current_exp = player.skill_exp.get(skill_name, 0)
        new_exp = current_exp + exp_gain
        player.skill_exp[skill_name] = new_exp

        new_level = self.recalculate_skill_level(skill_name, new_exp)
        skill_index = -1
        old_level = 0
        for i, skill in enumerate(player.skills):
            if skill.name == skill_name:
                skill_index = i
                old_level = skill.level
                break

        leveled_up = False
        if skill_index >= 0 and new_level > old_level:
            player.skills[skill_index].level = new_level
            leveled_up = True
            msg = f"技能【{skill_name}】升级到了Lv.{new_level}！"
        else:
            msg = f"技能【{skill_name}】经验 +{exp_gain}"

        if player.growth_log is None:
            player.growth_log = []
        player.growth_log.append(msg)

        self.update_player(
            ctx,
            {
                "skill_exp": player.skill_exp,
                "skills": [s.model_dump() for s in player.skills],
                "growth_log": player.growth_log,
            },
        )
        return {
            "skill": skill_name,
            "exp_gained": exp_gain,
            "leveled_up": leveled_up,
            "new_level": new_level if leveled_up else old_level,
        }

    def apply_hp_effect_from_check(
        self, ctx: Optional[GameContext], success: bool, critical: bool, fumble: bool
    ) -> dict:
        player = self.get_player(ctx)
        if not player:
            return {}

        hp_change = 0
        msg = ""
        if critical:
            hp_change = 2
            msg = f"大成功让你士气大振，恢复 {hp_change} 点HP。"
        elif fumble:
            hp_change = -3
            msg = f"严重的失误导致你受伤，扣除 {-hp_change} 点HP。"
        elif not success:
            hp_change = -1
            msg = f"行动受挫，扣除 {-hp_change} 点HP。"

        if hp_change != 0:
            new_player = self.update_hp(ctx, hp_change)
            if new_player:
                if new_player.growth_log is None:
                    new_player.growth_log = []
                new_player.growth_log.append(msg)
                self.update_player(ctx, {"growth_log": new_player.growth_log})
            return {"hp_change": hp_change, "current_hp": new_player.current_hp if new_player else player.current_hp}
        return {"hp_change": 0, "current_hp": player.current_hp}

    def recalculate_skill_level(self, skill_name: str, exp: int) -> int:
        thresholds = [0, 20, 50, 100, 200, 400]
        level = 1
        for i, threshold in enumerate(thresholds):
            if exp >= threshold:
                level = i + 1
        return level

    def clear_growth_log(self, ctx: Optional[GameContext]) -> None:
        player = self.get_player(ctx)
        if player and player.growth_log:
            self.update_player(ctx, {"growth_log": []})

    def _find_skill_info(self, name: str, scenario_type: str) -> Optional[dict]:
        skills_map = get_preset_skills_for_scenario(scenario_type)
        for category, skills in skills_map.items():
            for skill_data in skills:
                if skill_data["name"] == name:
                    return {
                        "category": category,
                        "description": skill_data["description"],
                        "related_attribute": skill_data["related_attribute"],
                    }
        return LEGACY_SKILL_INDEX.get(name)

    def _normalize_skill_payload(
        self,
        skill_update: dict,
        scenario_type: str,
        existing_skills: Optional[List[dict]] = None,
    ) -> dict:
        skill_name = skill_update.get("name", "")
        skill_level = skill_update.get("level", 1)
        skill_info = self._find_skill_info(skill_name, scenario_type)

        if skill_info:
            return {
                "id": skill_update.get("id", f"skill_{uuid.uuid4().hex[:6]}"),
                "name": skill_name,
                "category": skill_update.get("category", skill_info["category"]),
                "level": skill_level,
                "description": skill_update.get("description", skill_info["description"]),
                "related_attribute": skill_update.get(
                    "related_attribute", skill_info["related_attribute"]
                ),
            }

        existing_match = None
        for existing in existing_skills or []:
            if isinstance(existing, dict) and existing.get("name") == skill_name:
                existing_match = existing
                break

        return {
            "id": skill_update.get(
                "id",
                (existing_match or {}).get("id", f"skill_{uuid.uuid4().hex[:6]}"),
            ),
            "name": skill_name or "未命名技能",
            "category": skill_update.get(
                "category",
                (existing_match or {}).get("category", "custom"),
            ),
            "level": skill_level,
            "description": skill_update.get(
                "description",
                (existing_match or {}).get("description", "LLM 生成的场景专属技能"),
            ),
            "related_attribute": skill_update.get(
                "related_attribute",
                (existing_match or {}).get("related_attribute", "wisdom"),
            ),
        }

    def get_skill_modifier(self, ctx: Optional[GameContext], skill_name: str) -> int:
        player = self.get_player(ctx)
        if not player:
            return 0
        for skill in player.skills:
            if skill.name == skill_name:
                return skill.level
        return 0

    def get_player_summary(self, ctx: Optional[GameContext]) -> str:
        player = self.get_player(ctx)
        if not player:
            return ""
        summary_parts = [
            f"【{player.name}】",
            f"称号: {player.title or '未知'}",
            f"出身/血统: {player.race or '未知'}",
            f"年龄: {player.age or '未知'}",
            f"背景: {player.background or '未知'}",
        ]
        summary_parts.append("属性:")
        summary_parts.append(f"  力量 {player.strength} ({(player.strength - 10) // 2:+d})")
        summary_parts.append(f"  敏捷 {player.dexterity} ({(player.dexterity - 10) // 2:+d})")
        summary_parts.append(f"  体质 {player.constitution} ({(player.constitution - 10) // 2:+d})")
        summary_parts.append(f"  智力 {player.intelligence} ({(player.intelligence - 10) // 2:+d})")
        summary_parts.append(f"  感知 {player.wisdom} ({(player.wisdom - 10) // 2:+d})")
        summary_parts.append(f"  魅力 {player.charisma} ({(player.charisma - 10) // 2:+d})")
        summary_parts.append(f"HP: {player.current_hp}/{player.max_hp}")
        if player.skills:
            summary_parts.append("技能:")
            for skill in player.skills:
                summary_parts.append(f"  - {skill.name} (Lv.{skill.level})")
        return "\n".join(summary_parts)

    async def generate_player_with_llm(
        self, ctx: GameContext, world_setting: str = "", scenario_type: Optional[str] = None
    ) -> Optional[PlayerCharacter]:
        scenario_type = self._resolve_scenario_type(ctx, scenario_type)
        game_info = self.game_repository.get_game_info(ctx.game_id) or {}
        campaign_brief = game_info.get("campaign_brief", "")

        try:
            prompt = build_player_generation_prompt(
                scenario_type, world_setting or game_info.get("world_setting", ""), campaign_brief
            )
            player_data = await self.llm_adapter.generate_json(
                ctx=ctx,
                prompt=prompt,
                system_prompt=f"你是一个专业的角色设计师，专精{get_scenario_profile(scenario_type).label}。",
                timeout=120,
                max_tokens=2500,
            )

            if not player_data or not isinstance(player_data, dict):
                logger.warning("LLM返回格式错误，无法解析角色数据")
                return None

            for field in ["name", "age", "gender", "race"]:
                if field not in player_data:
                    logger.warning("LLM返回数据缺少必要字段: %s", field)
                    return None

            skills: List[PlayerSkill] = []
            if isinstance(player_data.get("skills"), list):
                for skill_data in player_data["skills"]:
                    if isinstance(skill_data, dict):
                        base_info = self._find_skill_info(skill_data.get("name", ""), scenario_type) or {}
                        skills.append(
                            PlayerSkill(
                                id=f"skill_{uuid.uuid4().hex[:6]}",
                                name=skill_data.get("name", "未知技能"),
                                category=skill_data.get("category", base_info.get("category", "general")),
                                level=skill_data.get("level", 1),
                                description=skill_data.get("description", base_info.get("description", "")),
                                related_attribute=skill_data.get(
                                    "related_attribute", base_info.get("related_attribute", "strength")
                                ),
                            )
                        )

            constitution = player_data.get("constitution", 10)
            max_hp = self.calculate_max_hp(constitution)
            background = player_data.get("background", "一位神秘的冒险者")
            motivation = player_data.get("motivation", "")
            if motivation:
                background = f"{background}\n\n核心动机：{motivation}"

            player = PlayerCharacter(
                id="player",
                name=player_data.get("name", "冒险者"),
                age=player_data.get("age", 20),
                gender=player_data.get("gender", "其他"),
                race=player_data.get("race", get_scenario_profile(scenario_type).player_races[0]),
                title=player_data.get("title", ""),
                background=background,
                appearance=player_data.get("appearance", "看起来充满决心"),
                personality=player_data.get("personality", ""),
                scenario_type=scenario_type,
                strength=player_data.get("strength", 10),
                dexterity=player_data.get("dexterity", 10),
                constitution=constitution,
                intelligence=player_data.get("intelligence", 10),
                wisdom=player_data.get("wisdom", 10),
                charisma=player_data.get("charisma", 10),
                max_hp=max_hp,
                current_hp=max_hp,
                skills=skills,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            self.player_repository.save(ctx, player.model_dump())
            logger.info("主角生成成功: %s", player.name)
            return player
        except Exception as exc:
            logger.exception("LLM生成角色失败: %s", str(exc))
            return None
