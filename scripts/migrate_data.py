import os
import json
import shutil
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
GAMES_DIR = os.path.join(BASE_DIR, "games")


def migrate_existing_data():
    if not os.path.exists(DATA_DIR):
        print("没有找到旧数据目录，无需迁移")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    game_id = f"game_{timestamp}"
    game_dir = os.path.join(GAMES_DIR, game_id)
    
    os.makedirs(game_dir, exist_ok=True)
    
    subdirs = ["memory", "novel", "character", "player", "saves", "snapshots"]
    for subdir in subdirs:
        os.makedirs(os.path.join(game_dir, subdir), exist_ok=True)
    
    game_info = {
        "game_id": game_id,
        "created_at": datetime.now().isoformat(),
        "world_setting": "迁移的旧游戏数据",
        "status": "migrated"
    }
    
    with open(os.path.join(game_dir, "game_info.json"), "w", encoding="utf-8") as f:
        json.dump(game_info, f, ensure_ascii=False, indent=2)
    
    migrations = []
    
    old_chars_dir = os.path.join(DATA_DIR, "characters")
    if os.path.exists(old_chars_dir):
        new_chars_dir = os.path.join(game_dir, "character")
        for filename in os.listdir(old_chars_dir):
            if filename.endswith(".json"):
                src = os.path.join(old_chars_dir, filename)
                dst = os.path.join(new_chars_dir, filename)
                shutil.copy2(src, dst)
                migrations.append(f"角色: {filename}")
    
    old_memory_dir = os.path.join(BASE_DIR, "memory")
    if os.path.exists(old_memory_dir):
        new_memory_dir = os.path.join(game_dir, "memory")
        for filename in os.listdir(old_memory_dir):
            src = os.path.join(old_memory_dir, filename)
            dst = os.path.join(new_memory_dir, filename)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                migrations.append(f"记忆: {filename}")
    
    old_novels_dir = os.path.join(BASE_DIR, "novels")
    if os.path.exists(old_novels_dir):
        new_novels_dir = os.path.join(game_dir, "novel")
        for folder in os.listdir(old_novels_dir):
            src_folder = os.path.join(old_novels_dir, folder)
            if os.path.isdir(src_folder):
                dst_folder = os.path.join(new_novels_dir, folder)
                shutil.copytree(src_folder, dst_folder)
                migrations.append(f"小说: {folder}")
    
    old_player_dir = os.path.join(DATA_DIR, "player")
    if os.path.exists(old_player_dir):
        new_player_dir = os.path.join(game_dir, "player")
        for filename in os.listdir(old_player_dir):
            if filename.endswith(".json"):
                src = os.path.join(old_player_dir, filename)
                dst = os.path.join(new_player_dir, filename)
                shutil.copy2(src, dst)
                migrations.append(f"玩家: {filename}")
    
    old_saves_dir = os.path.join(DATA_DIR, "saves")
    if os.path.exists(old_saves_dir):
        new_saves_dir = os.path.join(game_dir, "saves")
        for filename in os.listdir(old_saves_dir):
            if filename.endswith(".json"):
                src = os.path.join(old_saves_dir, filename)
                dst = os.path.join(new_saves_dir, filename)
                shutil.copy2(src, dst)
                migrations.append(f"存档: {filename}")
    
    old_snapshots_dir = os.path.join(DATA_DIR, "snapshots")
    if os.path.exists(old_snapshots_dir):
        new_snapshots_dir = os.path.join(game_dir, "snapshots")
        for filename in os.listdir(old_snapshots_dir):
            if filename.endswith(".json"):
                src = os.path.join(old_snapshots_dir, filename)
                dst = os.path.join(new_snapshots_dir, filename)
                shutil.copy2(src, dst)
                migrations.append(f"快照: {filename}")
    
    print(f"\n迁移完成！")
    print(f"新游戏ID: {game_id}")
    print(f"迁移的项目:")
    for m in migrations:
        print(f"  - {m}")
    
    return game_id


if __name__ == "__main__":
    migrate_existing_data()
