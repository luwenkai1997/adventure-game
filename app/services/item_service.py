import re
from typing import Any, Dict, List, Optional

from app.game_context import GameContext


class ItemService:
    def __init__(self, player_repository):
        self.player_repository = player_repository

    def use_item(self, ctx: Optional[GameContext], item_id: str) -> Dict[str, Any]:
        player = self.player_repository.load(ctx)
        items = player.get("inventory", [])
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            return {"success": False, "error": "物品不存在"}
        if item.get("type") not in ["consumable"]:
            return {"success": False, "error": "该物品不能使用"}

        result = self._apply_item_effects(player, item)

        item["qty"] = item.get("qty", 1) - 1
        player["inventory"] = [i for i in items if i.get("qty", 0) > 0]
        self.player_repository.save(ctx, player)

        return {"success": True, "result": result}

    def toggle_equip(self, ctx: Optional[GameContext], item_id: str) -> Dict[str, Any]:
        player = self.player_repository.load(ctx)
        items = player.get("inventory", [])
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            return {"success": False, "error": "物品不存在"}
        if item.get("type") not in ["weapon", "armor"]:
            return {"success": False, "error": "该物品不可装备"}

        item["equipped"] = not item.get("equipped", False)

        if item["equipped"]:
            for other in items:
                if other.get("id") != item_id and other.get("type") == item.get("type"):
                    other["equipped"] = False

        self.player_repository.save(ctx, player)
        return {"success": True, "equipped": item["equipped"], "item": item}

    def _apply_item_effects(self, player: Dict, item: Dict) -> Dict[str, Any]:
        effects = item.get("effects", [])
        result: Dict[str, Any] = {"healed": 0}
        for effect in effects:
            hp_match = re.search(r'(\d+)\s*(HP|生命|点生命)', str(effect))
            if hp_match:
                heal = int(hp_match.group(1))
                player["current_hp"] = min(
                    player.get("current_hp", 10) + heal,
                    player.get("max_hp", 10),
                )
                result["healed"] = heal
        return result

    def get_equipment(self, ctx: Optional[GameContext]) -> Dict[str, Any]:
        player = self.player_repository.load(ctx)
        items = player.get("inventory", [])
        equipped = [i for i in items if i.get("equipped")]

        check_bonus: Dict[str, int] = {}
        attack_bonus = 0
        defense = 0
        hp_bonus = 0

        for item in equipped:
            stats = item.get("stats", {})
            attack_bonus += stats.get("attack_bonus", 0)
            defense += stats.get("defense", 0)
            hp_bonus += stats.get("hp_bonus", 0)
            for attr, val in stats.get("check_bonus", {}).items():
                check_bonus[attr] = check_bonus.get(attr, 0) + val

        return {
            "equipped": equipped,
            "bonuses": {
                "attack_bonus": attack_bonus,
                "defense": defense,
                "hp_bonus": hp_bonus,
                "check_bonus": check_bonus,
            },
        }

    def get_equipment_check_bonus(self, ctx: Optional[GameContext], attribute: str) -> int:
        player = self.player_repository.load(ctx)
        if not player:
            return 0
        bonus = 0
        for item in player.get("inventory", []):
            if item.get("equipped") and item.get("stats"):
                check_bonus = item["stats"].get("check_bonus", {})
                bonus += check_bonus.get(attribute, 0)
        return bonus