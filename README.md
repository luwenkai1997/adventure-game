# 文字冒险游戏

一个基于 AI 的沉浸式文字冒险游戏，支持自定义世界观，通过选择推动剧情发展。

## 功能特点

### 核心功能
- **自定义世界观设定** - 赛博朋克、古代江湖、末日废土、深海科研站等任意世界
- **AI 动态生成剧情和选项** - 每次选择都会触发新的剧情发展
- **多种结局** - 好结局/坏结局/中立结局，由玩家选择倾向决定
- **深色终端风格界面** - 复古科幻风格的视觉体验

### 角色系统
- **AI 生成主角** - 根据世界观自动生成契合的主角角色
- **NPC 自动生成** - 包含主角、反派、配角等完整角色体系
- **角色关系网络** - 可视化展示角色之间的关系
- **角色属性系统** - 力量、敏捷、智力、魅力等六维属性

### 游戏体验
- **智能剧情记录** - 自动更新 memory.md 记录故事发展
- **第4个自定义选项** - 可以自由输入故事发展方向
- **选择结局类型** - 结束游戏时可指定结局类型
- **右侧日志面板** - 实时显示每轮故事发展
- **骰子检定系统** - 支持技能检定，增加游戏策略性

### 数据管理
- **游戏数据隔离** - 每个游戏独立存储，互不干扰
- **游戏列表管理** - 可查看、加载、删除历史游戏
- **多存档位** - 支持5个存档位，随时保存/加载
- **回退功能** - 支持撤销最近10步操作

### 小说生成
- **一键生成小说** - 游戏结束后根据记忆文档创作完整小说
- **分章节生成** - 按游戏轮次自动规划章节数量
- **实时进度反馈** - 显示生成进度和预计时间
- **小说导出** - 生成 Markdown 格式，方便阅读和分享

## 运行步骤

### 1. 安装 uv

如果还没有安装 uv，请先安装：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 同步依赖

```bash
uv sync
```

### 3. 配置 API

复制 `.env.example` 为 `.env`，填入你的 API 配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
API_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
API_MODEL=ark-code-latest
API_KEY=你的API密钥
```

### 4. 运行服务器

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

### 5. 开始游戏

打开浏览器访问 `http://localhost:8080`

## 项目结构

```
adventure-game/
├── server.py              # FastAPI 后端服务器入口
├── index.html             # 前端游戏页面（HTML + CSS + JS）
├── pyproject.toml         # 项目依赖配置
├── .env                   # API 配置（本地，不上传）
├── .env.example           # 示例配置文件
├── .gitignore             # Git 忽略规则
├── README.md              # 项目说明
├── app/
│   ├── api/               # API 路由层
│   │   ├── game_routes.py       # 游戏核心路由（聊天、记忆、游戏管理）
│   │   ├── character_routes.py  # 角色管理路由
│   │   ├── player_routes.py     # 玩家角色路由
│   │   ├── novel_routes.py      # 小说生成路由
│   │   ├── save_routes.py       # 存档管理路由
│   │   └── check_routes.py      # 骰子检定路由
│   ├── models/            # 数据模型层
│   │   ├── character.py         # 角色数据模型
│   │   ├── player.py            # 玩家数据模型
│   │   ├── novel.py             # 小说数据模型
│   │   ├── save.py              # 存档数据模型
│   │   └── check.py             # 检定数据模型
│   ├── services/          # 业务逻辑层
│   │   ├── game_service.py      # 游戏核心服务
│   │   ├── character_service.py # 角色生成服务
│   │   ├── player_service.py    # 玩家角色服务
│   │   ├── novel_service.py     # 小说生成服务
│   │   ├── save_service.py      # 存档管理服务
│   │   └── check_service.py     # 检定计算服务
│   ├── utils/             # 工具层
│   │   ├── game_manager.py      # 游戏管理（创建、加载、删除）
│   │   ├── file_storage.py      # 文件存储操作
│   │   └── llm_client.py        # LLM API 调用封装
│   └── config.py          # 配置文件（Prompt模板、常量）
├── games/                 # 游戏数据目录
│   └── game_YYYYMMDDHHMMSS/     # 单个游戏目录
│       ├── game_info.json       # 游戏元信息
│       ├── memory/              # 游戏记忆
│       │   └── memory.md
│       ├── character/           # 角色数据
│       │   ├── char_xxx.json
│       │   └── relations.json
│       ├── player/              # 玩家角色
│       │   └── player.json
│       ├── novel/               # 生成的小说
│       │   └── novel-timestamp/
│       ├── saves/               # 游戏存档
│       │   ├── save_1.json
│       │   └── history.json
│       └── snapshots/           # 角色快照
└── scripts/               # 工具脚本
    ├── migrate_data.py          # 数据迁移脚本
    └── test_game_isolation.py   # 数据隔离测试
```

## 游戏玩法

1. 在开始页输入你想探索的世界观描述
2. 点击"开始新游戏"，系统会：
   - 创建独立游戏目录
   - 使用 AI 生成契合世界观的主角
   - 初始化游戏记忆文档
3. 阅读剧情，从三个预设选项中做出选择
4. 也可以输入自定义选项推进故事
5. 可随时点击"结束游戏"选择结局类型
6. 游戏结束后点击"生成小说"，创作完整小说
7. 通过"游戏列表"可以加载历史游戏继续冒险

## API 接口

### 游戏管理

#### POST /api/games/create
创建新游戏

**请求体**:
```json
{
  "world_setting": "赛博朋克新加坡"
}
```

**响应**:
```json
{
  "success": true,
  "game_id": "game_20240317143022"
}
```

#### GET /api/games
获取所有游戏列表

#### POST /api/games/load/{game_id}
加载指定游戏

#### DELETE /api/games/{game_id}
删除指定游戏

### 游戏核心

#### POST /api/chat
生成游戏剧情和选项

**请求体**:
```json
{
  "messages": [
    {"role": "user", "content": "开始游戏。世界观设定：..."}
  ],
  "extraPrompt": ""
}
```

#### POST /api/save-memory
保存初始世界观到 memory.md

#### POST /api/update-memory
更新游戏记忆文档

### 角色系统

#### GET /api/characters
获取当前游戏所有角色

#### GET /api/characters/graph
获取角色关系图数据

#### POST /api/characters/generate
生成角色（主角、反派、NPC等）

#### POST /api/npcs/generate
根据主角信息生成 NPC

### 玩家角色

#### POST /api/player/generate
使用 AI 生成主角角色

#### GET /api/player
获取当前玩家角色

#### PUT /api/player
更新玩家角色

### 小说生成

#### POST /api/novel/plan
规划小说章节

#### POST /api/novel/chapter
生成单个章节

#### POST /api/novel/merge
合并所有章节为完整小说

### 存档系统

#### GET /api/save/list
获取存档列表

#### POST /api/save/{slot_id}
保存游戏到指定存档位

#### GET /api/save/load/{slot_id}
加载指定存档

#### POST /api/history/undo
撤销上一步操作

## 技术架构

- **后端**: FastAPI + Python 3.10+
- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **AI模型**: 兼容 OpenAI API 格式的任意大模型
- **数据存储**: 文件系统（JSON + Markdown）
- **包管理**: uv

## 常见问题

### Q: 游戏进度会丢失吗？
A: 不会。游戏使用文件系统存储，每个游戏独立保存，支持多存档位。

### Q: 如何重新开始游戏？
A: 点击"开始新游戏"会创建全新的游戏目录，与历史游戏完全隔离。

### Q: 小说生成需要多长时间？
A: 通常需要 2-5 分钟，具体取决于故事长度。生成过程中会显示实时进度。

### Q: 可以导出游戏记录吗？
A: 游戏记录保存在 `games/game_xxx/memory/memory.md` 文件中，可以直接查看或分享。

### Q: 如何切换不同的游戏？
A: 点击"游戏列表"按钮，可以查看、加载或删除历史游戏。

## 开发说明

### 环境要求
- Python 3.10 或更高版本
- uv 包管理器

### 本地开发
```bash
# 安装依赖
uv sync

# 启动开发服务器（热重载）
uv run uvicorn server:app --host 0.0.0.0 --port 8080 --reload

# 访问应用
open http://localhost:8080
```

### 数据迁移
如果从旧版本升级，运行迁移脚本：
```bash
python3 scripts/migrate_data.py
```

### 测试数据隔离
```bash
python3 scripts/test_game_isolation.py
```

## 更新日志

### v0.3.0 (2024-03-20)
- 重构游戏数据存储结构，实现完全数据隔离
- 新增游戏管理功能（创建、加载、删除、列表）
- 每个游戏独立存储角色、记忆、小说、存档
- 新增游戏列表界面，支持切换历史游戏
- 优化时间戳精度，确保游戏ID唯一性
- 添加数据迁移脚本和测试脚本

### v0.2.0 (2024-03-17)
- 添加 localStorage 自动保存功能，游戏进度持久化
- 改进错误提示系统，提供更友好的错误信息
- 添加小说生成进度显示，实时反馈生成状态
- 优化游戏流程，小说改为游戏结束后统一生成
- 更新 README 文档，修正功能描述

### v0.1.0 (2024-03-15)
- 初始版本发布
- 基础游戏功能实现
- AI 剧情生成和选项系统
- 记忆文档和小说生成功能

## 许可证

MIT License
