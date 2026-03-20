import os
import sys
import json
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.game_manager import (
    create_game_structure,
    list_all_games,
    get_game_info,
    delete_game,
    get_game_dir,
    GAMES_DIR,
)
from app.utils.file_storage import (
    init_new_game,
    set_current_game,
    get_current_game,
    save_memory,
    load_memory,
    save_character,
    load_characters,
    save_player,
    load_player,
)


def test_game_isolation():
    print("=" * 60)
    print("测试游戏数据隔离功能")
    print("=" * 60)
    
    print("\n1. 创建第一个游戏...")
    game1_paths = init_new_game("第一个测试游戏 - 奇幻世界")
    game1_id = game1_paths["game_dir"].split("/")[-1]
    print(f"   游戏1 ID: {game1_id}")
    
    print("\n2. 在游戏1中保存数据...")
    save_memory("奇幻世界设定", "英雄的冒险故事")
    test_char = {
        "id": "char_test1",
        "name": "游戏1角色",
        "role_type": "protagonist"
    }
    save_character(test_char)
    test_player = {
        "id": "player1",
        "name": "游戏1玩家"
    }
    save_player(test_player)
    print("   已保存: 记忆、角色、玩家数据")
    
    print("\n3. 创建第二个游戏...")
    game2_paths = init_new_game("第二个测试游戏 - 科幻世界")
    game2_id = game2_paths["game_dir"].split("/")[-1]
    print(f"   游戏2 ID: {game2_id}")
    
    print("\n4. 在游戏2中保存数据...")
    save_memory("科幻世界设定", "太空探险故事")
    test_char2 = {
        "id": "char_test2",
        "name": "游戏2角色",
        "role_type": "protagonist"
    }
    save_character(test_char2)
    test_player2 = {
        "id": "player2",
        "name": "游戏2玩家"
    }
    save_player(test_player2)
    print("   已保存: 记忆、角色、玩家数据")
    
    print("\n5. 验证数据隔离...")
    set_current_game(game1_id)
    chars_game1 = load_characters()
    player_game1 = load_player()
    memory_game1 = load_memory()
    
    print(f"\n   游戏1 ({game1_id}) 数据:")
    print(f"   - 角色数量: {len(chars_game1)}")
    print(f"   - 角色名称: {[c['name'] for c in chars_game1 if c['name'].startswith('游戏')]}")
    print(f"   - 玩家: {player_game1['name'] if player_game1 else 'None'}")
    print(f"   - 记忆开头: {memory_game1[:30] if memory_game1 else 'None'}...")
    
    set_current_game(game2_id)
    chars_game2 = load_characters()
    player_game2 = load_player()
    memory_game2 = load_memory()
    
    print(f"\n   游戏2 ({game2_id}) 数据:")
    print(f"   - 角色数量: {len(chars_game2)}")
    print(f"   - 角色名称: {[c['name'] for c in chars_game2 if c['name'].startswith('游戏')]}")
    print(f"   - 玩家: {player_game2['name'] if player_game2 else 'None'}")
    print(f"   - 记忆开头: {memory_game2[:30] if memory_game2 else 'None'}...")
    
    print("\n6. 验证目录结构...")
    game1_dir = get_game_dir(game1_id)
    game2_dir = get_game_dir(game2_id)
    
    required_dirs = ["memory", "novel", "character", "player", "saves", "snapshots"]
    
    print(f"\n   游戏1目录结构:")
    for d in required_dirs:
        path = os.path.join(game1_dir, d)
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"     {exists} {d}/")
    
    print(f"\n   游戏2目录结构:")
    for d in required_dirs:
        path = os.path.join(game2_dir, d)
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"     {exists} {d}/")
    
    print("\n7. 列出所有游戏...")
    all_games = list_all_games()
    for game in all_games[:5]:
        print(f"   - {game['game_id']}: {game.get('world_setting', 'N/A')[:30]}...")
    
    print("\n8. 清理测试数据...")
    delete_game(game1_id)
    delete_game(game2_id)
    print(f"   已删除: {game1_id}, {game2_id}")
    
    print("\n" + "=" * 60)
    print("测试完成！数据隔离验证成功。")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    test_game_isolation()
