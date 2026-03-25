import random
import uuid
from typing import List, Optional
from datetime import datetime
from app.models.player import (
    PlayerCharacter,
    PlayerSkill,
    PlayerCreateRequest,
    PlayerRandomRequest,
    PRESET_SKILLS,
    ATTRIBUTE_NAMES_EN,
)
from app.utils.file_storage import save_player, load_player


class PlayerService:
    def __init__(self):
        pass

    def calculate_modifier(self, attribute: int) -> int:
        return (attribute - 10) // 2

    def calculate_max_hp(self, constitution: int) -> int:
        modifier = self.calculate_modifier(constitution)
        return 10 + modifier * 2

    def create_player(self, request: PlayerCreateRequest) -> PlayerCharacter:
        skills = []
        for skill_name in request.skills:
            skill = self._find_skill_by_name(skill_name)
            if skill:
                skills.append(skill)

        max_hp = self.calculate_max_hp(request.constitution)

        player = PlayerCharacter(
            id="player",
            name=request.name,
            age=request.age,
            gender=request.gender,
            race=request.race,
            background=request.background,
            appearance=request.appearance,
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

        save_player(player.model_dump())
        return player

    def random_player(
        self, request: Optional[PlayerRandomRequest] = None
    ) -> PlayerCharacter:
        gender_options = ["男", "女", "其他"]
        race_options = ["人类", "精灵", "矮人", "兽人", "其他"]

        gender = (
            request.gender
            if request and request.gender
            else random.choice(gender_options)
        )
        race = random.choice(race_options)

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

        skill_categories = list(PRESET_SKILLS.keys())
        num_skills = random.randint(2, 3)
        selected_categories = random.sample(
            skill_categories, min(num_skills, len(skill_categories))
        )

        skills = []
        for category in selected_categories:
            category_skills = PRESET_SKILLS[category]
            selected_skill = random.choice(category_skills)
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

        name_templates = {
            "男": ["李云", "张风", "王剑", "刘影", "陈墨", "周游", "吴寒", "郑锋"],
            "女": ["林婉", "苏雪", "周晴", "吴月", "郑岚", "陈烟", "刘露", "李梅"],
            "其他": ["无名", "行者", "孤影", "夜羽", "霜寒", "云烟", "风啸", "雷鸣"],
        }
        name = random.choice(name_templates.get(gender, name_templates["男"]))
        age = random.randint(18, 40)

        background_templates = [
            "曾是一名游历四方的侠客，见惯了世间百态",
            "出身于没落的武林世家，自幼习武",
            "原本是山野间的猎人，机缘巧合踏入江湖",
            "曾是某个门派的弟子，因故离开师门",
            "江湖郎中，精通医术和草药知识",
            "落魄书生，偶得武功秘籍自学成才",
        ]
        background = random.choice(background_templates)

        appearance_templates = {
            "人类": "普通人类外貌，但眼神中透着江湖历练",
            "精灵": "尖耳长发，气质出尘，行动间轻盈如风",
            "矮人": "身材矮小但敦实有力，胡须浓密",
            "兽人": "带有兽类特征，犬齿微露，目光锐利",
            "其他": "气质独特，让人难以看出来历",
        }
        appearance = appearance_templates.get(race, appearance_templates["其他"])

        max_hp = self.calculate_max_hp(attributes["constitution"])

        player = PlayerCharacter(
            id="player",
            name=name,
            age=age,
            gender=gender,
            race=race,
            background=background,
            appearance=appearance,
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

        save_player(player.model_dump())
        return player

    def get_player(self) -> Optional[PlayerCharacter]:
        player_data = load_player()
        if player_data:
            return PlayerCharacter(**player_data)
        return None

    def update_player(self, updates: dict) -> Optional[PlayerCharacter]:
        player_data = load_player()
        if not player_data:
            return None

        if "skills" in updates and isinstance(updates["skills"], list):
            from app.models.player import PRESET_SKILLS
            from uuid import uuid4

            processed_skills = []
            for skill_update in updates["skills"]:
                if isinstance(skill_update, dict):
                    skill_name = skill_update.get("name", "")
                    skill_level = skill_update.get("level", 1)

                    skill_info = self._find_skill_info(skill_name)
                    if skill_info:
                        processed_skill = {
                            "id": skill_update.get("id", f"skill_{uuid4().hex[:6]}"),
                            "name": skill_name,
                            "category": skill_info["category"],
                            "level": skill_level,
                            "description": skill_info["description"],
                            "related_attribute": skill_info["related_attribute"],
                        }
                        processed_skills.append(processed_skill)
                    else:
                        processed_skill = {
                            "id": skill_update.get("id", f"skill_{uuid4().hex[:6]}"),
                            "name": skill_name,
                            "category": skill_update.get("category", "general"),
                            "level": skill_level,
                            "description": skill_update.get("description", ""),
                            "related_attribute": skill_update.get(
                                "related_attribute", "strength"
                            ),
                        }
                        processed_skills.append(processed_skill)
                else:
                    processed_skills.append(skill_update)

            updates["skills"] = processed_skills

        player_data.update(updates)
        player_data["updated_at"] = datetime.now().isoformat()

        if "constitution" in updates:
            player_data["max_hp"] = self.calculate_max_hp(updates["constitution"])
            if "current_hp" not in updates:
                player_data["current_hp"] = player_data["max_hp"]

        save_player(player_data)
        return PlayerCharacter(**player_data)

    def add_skill(self, skill_name: str) -> Optional[PlayerCharacter]:
        player = self.get_player()
        if not player:
            return None

        skill = self._find_skill_by_name(skill_name)
        if not skill:
            return None

        for existing_skill in player.skills:
            if existing_skill.name == skill_name:
                return player

        player.skills.append(skill)
        return self.update_player({"skills": [s.model_dump() for s in player.skills]})

    def remove_skill(self, skill_name: str) -> Optional[PlayerCharacter]:
        player = self.get_player()
        if not player:
            return None

        player.skills = [s for s in player.skills if s.name != skill_name]
        return self.update_player({"skills": [s.model_dump() for s in player.skills]})

    def update_hp(self, delta: int) -> Optional[PlayerCharacter]:
        player = self.get_player()
        if not player:
            return None

        new_hp = player.current_hp + delta
        new_hp = max(0, min(new_hp, player.max_hp))

        return self.update_player({"current_hp": new_hp})

    def _find_skill_by_name(self, name: str) -> Optional[PlayerSkill]:
        for category, skills in PRESET_SKILLS.items():
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
        return None

    def _find_skill_info(self, name: str) -> Optional[dict]:
        for category, skills in PRESET_SKILLS.items():
            for skill_data in skills:
                if skill_data["name"] == name:
                    return {
                        "category": category,
                        "description": skill_data["description"],
                        "related_attribute": skill_data["related_attribute"],
                    }
        return None

    def get_skill_modifier(self, skill_name: str) -> int:
        player = self.get_player()
        if not player:
            return 0

        for skill in player.skills:
            if skill.name == skill_name:
                return skill.level
        return 0

    def get_player_summary(self) -> str:
        player = self.get_player()
        if not player:
            return ""

        summary_parts = [
            f"【{player.name}】",
            f"种族: {player.race or '未知'}",
            f"年龄: {player.age or '未知'}",
            f"背景: {player.background or '未知'}",
        ]

        summary_parts.append("属性:")
        summary_parts.append(
            f"  力量 {player.strength} ({(player.strength - 10) // 2:+d})"
        )
        summary_parts.append(
            f"  敏捷 {player.dexterity} ({(player.dexterity - 10) // 2:+d})"
        )
        summary_parts.append(
            f"  体质 {player.constitution} ({(player.constitution - 10) // 2:+d})"
        )
        summary_parts.append(
            f"  智力 {player.intelligence} ({(player.intelligence - 10) // 2:+d})"
        )
        summary_parts.append(f"  感知 {player.wisdom} ({(player.wisdom - 10) // 2:+d})")
        summary_parts.append(
            f"  魅力 {player.charisma} ({(player.charisma - 10) // 2:+d})"
        )

        summary_parts.append(f"HP: {player.current_hp}/{player.max_hp}")

        if player.skills:
            summary_parts.append("技能:")
            for skill in player.skills:
                summary_parts.append(f"  - {skill.name} (Lv.{skill.level})")

        return "\n".join(summary_parts)

    async def generate_player_with_llm(self, world_setting: str = "") -> Optional[PlayerCharacter]:
        """使用LLM根据故事设定生成主角"""
        from app.config import PLAYER_GENERATION_PROMPT
        from app.utils.llm_client import call_llm, parse_json_response
        from uuid import uuid4
        
        try:
            prompt = PLAYER_GENERATION_PROMPT.format(world_setting=world_setting or "一个神秘的冒险世界")
            
            response = await call_llm(
                prompt, 
                "你是一个专业的角色设计师，擅长创造符合故事设定的有趣角色。请严格按照JSON格式返回。",
                timeout=90,
                max_tokens=2500
            )
            
            player_data = parse_json_response(response)
            
            if not player_data or not isinstance(player_data, dict):
                print("LLM返回格式错误，无法解析角色数据")
                return None
            
            required_fields = ['name', 'age', 'gender', 'race']
            for field in required_fields:
                if field not in player_data:
                    print(f"LLM返回数据缺少必要字段: {field}")
                    return None
            
            skills = []
            if 'skills' in player_data and isinstance(player_data['skills'], list):
                for skill_data in player_data['skills']:
                    if isinstance(skill_data, dict):
                        skills.append(PlayerSkill(
                            id=f"skill_{uuid4().hex[:6]}",
                            name=skill_data.get('name', '未知技能'),
                            category=skill_data.get('category', 'general'),
                            level=skill_data.get('level', 1),
                            description=skill_data.get('description', ''),
                            related_attribute=skill_data.get('related_attribute', 'strength')
                        ))
            
            constitution = player_data.get('constitution', 10)
            max_hp = self.calculate_max_hp(constitution)
            
            background = player_data.get('background', '一位神秘的冒险者')
            motivation = player_data.get('motivation', '')
            if motivation:
                background = f"{background}\n\n核心动机：{motivation}"
            
            player = PlayerCharacter(
                id="player",
                name=player_data.get('name', '冒险者'),
                age=player_data.get('age', 20),
                gender=player_data.get('gender', '其他'),
                race=player_data.get('race', '人类'),
                title=player_data.get('title', ''),
                background=background,
                appearance=player_data.get('appearance', '看起来充满决心'),
                personality=player_data.get('personality', ''),
                strength=player_data.get('strength', 10),
                dexterity=player_data.get('dexterity', 10),
                constitution=constitution,
                intelligence=player_data.get('intelligence', 10),
                wisdom=player_data.get('wisdom', 10),
                charisma=player_data.get('charisma', 10),
                max_hp=max_hp,
                current_hp=max_hp,
                skills=skills,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            save_player(player.model_dump())
            print(f"主角生成成功: {player.name}")
            return player
            
        except Exception as e:
            print(f"LLM生成角色失败: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
