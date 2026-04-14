# 文字冒险游戏

一个基于 AI 的沉浸式文字冒险游戏，支持自定义世界观，通过选择推动剧情发展。

## 功能特点

### 核心功能
- **自定义世界观设定** - 赛博朋克、古代江湖、末日废土、深海科研站等任意世界
- **AI 动态生成剧情和选项** - 每次选择都会触发新的剧情发展
- **多种结局** - 好结局/坏结局/中立结局，由玩家选择倾向决定
- **深色终端风格界面** - 复古科幻风格的视觉体验
- **故事设定扩展** - AI 自动将简短设定扩展为完整世界观

### 规则驱动技能成长（新）
- **技能经验与升级** - 使用技能进行骰子检定时，根据结果获得经验（大成功+20，成功+10，失败+5）。经验达到阈值（20/50/100/200/400）时自动升级。
- **HP 动态反馈** - 带有防御或生存属性的检定结果会直接影响主角生命值（大成功恢复HP，失败或大失败扣除HP）。
- **即时状态反馈** - 检定结果面板与日志区会实时展示技能升级与 HP 变化。

### 五维结局追踪系统（新）
- **五大路线积分** - 玩家的倾向选择会积累到五大神秘路线（救赎、力量、献祭、背叛、退隐）中，关键抉择提供额外积分加成。
- **命运前兆提示** - 随着某一路线积分领先，系统会在剧情中穿插特定路线的专属「命运前兆」与「路线指引」文案，引导玩家。
- **结局复盘总结** - 游戏结尾时会自动统计并展示本次冒险的路线评分及所作出的所有「关键抉择」。

### 选择倾向系统（新）
- **六维性格画像** - 每个选项标注倾向标签（勇敢/谨慎、善良/冷酷、理性/感性、正义/自利、仁慈/残忍、坦诚/狡诈），玩家的选择累积形成独特的性格画像
- **关键抉择** - 约每5轮出现一次「命运转折点」，以醒目样式标记，选择会被记录并在结局时回顾
- **后果预览** - 高感知（wisdom≥14）的角色可看到部分选项的后果提示，增加策略深度
- **性格驱动叙事** - AI 叙述者会根据玩家的性格倾向数据调整剧情走向和 NPC 反应

### NPC 对话与关系反馈（新）
- **NPC 实时对话** - 在游戏中可以直接点击 NPC 发起对话，AI 以该角色的性格、背景和与玩家的关系进行角色扮演式回应
- **关系变化反馈** - 每轮选择后，日志面板实时显示与相关 NPC 的关系变化（如"与[角色名]的信任度 +15"）
- **AI 驱动的关系演变** - 剧情中涉及 NPC 的选择会自动触发关系强度更新，关系数据持久化到角色关系图谱中

### 角色系统
- **AI 生成主角** - 根据世界观自动生成契合的主角角色
- **NPC 自动生成** - 包含主角、反派、配角等完整角色体系
- **角色关系网络** - 可视化展示角色之间的关系，关系强度随剧情动态变化
- **角色属性系统** - 力量、敏捷、智力、魅力等六维属性
- **技能系统** - 战斗、社交、知识、生存四大类共20种预设技能

### 游戏体验
- **智能剧情记录** - 自动更新 memory.md 记录故事发展
- **第4个自定义选项** - 可以自由输入故事发展方向
- **选择结局类型** - 结束游戏时可指定结局类型
- **右侧日志面板** - 实时显示每轮故事发展及关系变化
- **骰子检定系统** - 支持 D20 检定，增加游戏策略性

### 数据管理
- **游戏数据隔离** - 每个游戏独立存储，互不干扰
- **游戏列表管理** - 可查看、加载、删除历史游戏
- **多存档位** - 支持5个存档位，随时保存/加载
- **回退功能** - 支持撤销最近10步操作
- **LLM 调用日志** - 记录所有 AI 对话，便于调试

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

**注意**：本项目兼容任何支持 OpenAI API 格式的大模型服务。

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
├── index.html             # 前端页面壳（引用静态资源）
├── static/                # 前端静态资源
│   ├── css/styles.css     # 样式
│   └── js/app.js          # 游戏逻辑脚本
├── LICENSE                # MIT 许可证
├── Dockerfile             # 容器构建
├── docker-compose.yml     # 本地/部署编排
├── tests/                 # pytest 测试
├── pyproject.toml         # 项目依赖配置
├── .env                   # API 配置（本地，不上传）
├── .env.example           # 示例配置文件
├── .gitignore             # Git 忽略规则
├── README.md              # 项目说明
├── app/
│   ├── __init__.py        # 包初始化
│   ├── config.py          # 配置文件（Prompt模板、常量、API配置）
│   ├── errors.py          # 业务异常扩展
│   ├── http_client.py     # 共享异步 HTTP 客户端连接池
│   ├── logging_config.py  # 项目日志配置
│   ├── request_context.py # 并发安全请求上下文
│   ├── middleware/        # 请求生命周期与 Session 相关中间件
│   ├── api/               # API 路由层
│   │   ├── __init__.py
│   │   ├── game_routes.py       # 游戏核心路由（聊天、记忆、游戏管理、故事扩展）
│   │   ├── character_routes.py  # 角色管理路由（角色、关系、NPC生成）
│   │   ├── player_routes.py     # 玩家角色路由（创建、生成、属性、技能）
│   │   ├── novel_routes.py      # 小说生成路由（规划、章节、合并）
│   │   ├── save_routes.py       # 存档管理路由（存档、历史、回退）
│   │   └── check_routes.py      # 骰子检定路由（检定、掷骰）
│   ├── models/            # 数据模型层（Pydantic）
│   │   ├── __init__.py
│   │   ├── chat.py              # 聊天数据模型（ChoiceItem倾向标签、RelationshipChange、NPC对话）
│   │   ├── character.py         # 角色数据模型（CharacterCard、CharacterRelation等）
│   │   ├── player.py            # 玩家数据模型（PlayerCharacter、预设技能）
│   │   ├── save.py              # 存档数据模型（GameSave、HistorySnapshot）
│   │   └── check.py             # 检定数据模型（CheckRequest、CheckResult）
│   ├── services/          # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── game_service.py      # 游戏核心服务（聊天、记忆更新、关系变化处理）
│   │   ├── character_service.py # 角色生成服务（批量生成、关系生成、快照）
│   │   ├── player_service.py    # 玩家角色服务（创建、随机生成、LLM生成）
│   │   ├── novel_service.py     # 小说生成服务（规划、章节、合并）
│   │   ├── save_service.py      # 存档管理服务（存档列表、历史管理）
│   │   ├── check_service.py     # 检定计算服务（D20检定、叙述生成）
│   │   ├── prompt_composer.py   # Prompt 组合器（上下文、性格画像注入）
│   │   ├── chat_parser.py       # JSON 解析与容错验证服务
│   │   └── llm_gateway.py       # LLM 网关服务（并发限制机制、退避重试与取消流支持）
│   └── utils/             # 工具层
│       ├── __init__.py
│       ├── game_manager.py      # 游戏管理（创建、加载、删除、目录管理）
│       ├── file_storage.py      # 文件存储操作（角色、记忆、存档等）
│       ├── atomic_io.py         # 跨平台防损原子文件写入器
│       ├── path_security.py     # 目录穿越防御校验工具
│       └── json_utils.py        # 去中心化的多容错 JSON 文本清洗与提取
├── games/                 # 游戏数据目录
│   └── game_YYYYMMDDHHMMSS/     # 单个游戏目录
│       ├── game_info.json       # 游戏元信息
│       ├── llm-log.md           # LLM 调用日志
│       ├── memory/              # 游戏记忆
│       │   └── memory.md
│       ├── character/           # 角色数据
│       │   ├── char_xxx.json
│       │   └── relations.json
│       ├── player/              # 玩家角色
│       │   └── player.json
│       ├── novel/               # 生成的小说
│       │   └── novel-timestamp/
│       │       ├── plan.json
│       │       ├── chapters/
│       │       └── novel.md
│       ├── saves/               # 游戏存档
│       │   ├── save_1.json
│       │   └── history.json
│       └── snapshots/           # 角色快照
└── scripts/               # 工具脚本
    ├── migrate_data.py          # 数据迁移脚本
    └── test_game_isolation.py   # 数据隔离测试
```

## 游戏玩法

1. 在开始页输入你想探索的世界观描述（可使用「背景拓展」功能自动扩展）
2. 点击"开始新游戏"，系统会：
   - 创建独立游戏目录
   - 使用 AI 生成契合世界观的主角
   - 确认主角信息后自动生成 10 个 NPC 角色
   - 初始化游戏记忆文档
3. 阅读剧情，从三个预设选项中做出选择——每个选项带有倾向标签，你的选择会塑造角色性格画像
4. 也可以输入自定义选项推进故事
5. 留意标记为「命运转折点」的关键抉择，它们对结局影响最大
6. 点击角色面板中的 NPC 可发起对话，获取线索或推进关系
7. 关注日志面板中的关系变化提示，了解你的选择如何影响 NPC 关系
8. 可随时点击"结束游戏"选择结局类型
9. 游戏结束后点击"生成小说"，创作完整小说
10. 通过"游戏列表"可以加载历史游戏继续冒险

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
  "game_id": "game_20240317143022",
  "paths": {...}
}
```

#### GET /api/games
获取所有游戏列表

#### GET /api/games/current
获取当前游戏信息

#### POST /api/games/load/{game_id}
加载指定游戏

#### PUT /api/games/{game_id}
更新游戏信息

#### DELETE /api/games/{game_id}
删除指定游戏

#### WebSocket `/ws/chat/stream`（可选，替代 SSE）

- 连接时在查询串带上与 HTTP 相同的会话：`?session_id=<tab会话ID>`（与请求头 `X-Adventure-Session-ID` 一致）。
- 建立连接后发送一条 JSON，字段与 `POST /api/chat` 相同：`messages`、`extraPrompt`、`turn_context`。
- 服务端推送 JSON 帧：`type` 为 `chunk`（含 `content`）、`done`（含解析后的 `content`）、`error` 或 `cancelled`。

#### POST /api/story/expand
扩展故事设定（AI 自动补全世界观）

**请求体**:
```json
{
  "user_input": "赛博朋克新加坡"
}
```

### 游戏核心

#### POST /api/chat
生成游戏剧情和选项

**请求体**:
```json
{
  "messages": [
    {"role": "user", "content": "开始游戏。世界观设定：..."}
  ],
  "extraPrompt": "",
  "turn_context": {
    "last_check": null
  }
}
```

**响应** `content` 结构：
```json
{
  "scene": "剧情描述",
  "log": "本章概要",
  "choices": [
    {
      "text": "选项文本",
      "tendency": ["勇敢", "善良"],
      "is_key_decision": false,
      "consequence_hint": "后果预览（wisdom≥14可见）",
      "check": null,
      "check_optional": true
    }
  ],
  "ending_omen": "命运前兆（当某路线主导时出现，可选）",
  "route_hint": "当前主导路线指引（可选）",
  "relationship_changes": [
    {
      "character_name": "NPC名称",
      "change_type": "+",
      "value": 10,
      "reason": "帮助NPC解围"
    }
  ]
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
批量生成角色（主角、反派、配角、NPC）

#### POST /api/npcs/generate
根据主角信息生成 NPC（10个角色 + 关系网络）

#### POST /api/characters/{char_id}/dialogue
与指定 NPC 进行对话

**请求体**:
```json
{
  "message": "你知道关于古塔的秘密吗？",
  "context": "当前场景描述（可选）"
}
```

**响应**:
```json
{
  "success": true,
  "dialogue": "NPC的回复（符合角色性格）",
  "mood": "平静",
  "relationship_hint": "好感度上升"
}
```

#### GET /api/characters/snapshot/{chapter}
获取/创建角色快照

### 玩家角色

#### POST /api/player/create
手动创建玩家角色

#### POST /api/player/random
随机生成玩家角色

#### POST /api/player/generate
使用 LLM 根据世界观生成主角

#### GET /api/player
获取当前玩家角色

#### PUT /api/player
更新玩家角色

#### GET /api/player/skills
获取预设技能列表

### 小说生成

#### POST /api/novel/plan
规划小说章节（标题、章节大纲）

**响应**:
```json
{
  "novel_folder": "novel-20240317-143022",
  "plan": {
    "title": "小说标题",
    "total_chapters": 6,
    "chapters": [...]
  },
  "game_rounds": 10
}
```

#### POST /api/novel/chapter
生成单个章节

#### POST /api/novel/merge
合并所有章节为完整小说

#### GET /api/novel/status/{novel_folder}
获取小说生成状态

### 存档系统

#### GET /api/save/list
获取存档列表（5个存档位）

#### POST /api/save/{slot_id}
保存游戏到指定存档位

#### GET /api/save/load/{slot_id}
加载指定存档

#### DELETE /api/save/{slot_id}
删除存档

#### POST /api/history/undo
撤销上一步操作（最多10步）

### 检定系统

#### POST /api/check
执行 D20 检定

**请求体**:
```json
{
  "attribute": "strength",
  "skill": "剑术",
  "difficulty": 12,
  "description": "尝试撬开石门"
}
```

**响应**:
```json
{
  "success": true,
  "result": {
    "roll": 15,
    "modifier": 2,
    "skill_bonus": 2,
    "total": 19,
    "difficulty": 12,
    "success": true,
    "critical": false,
    "fumble": false,
    "narrative": "成功！投出15点...",
    "growth": {
      "exp_gain": 10,
      "skill": "剑术",
      "new_level": 2,
      "leveled_up": true,
      "hp_effect": 0
    }
  }
}
```

#### GET /api/check/roll
掷骰子（支持 d4/d6/d8/d10/d12/d20/d100）

## 技术架构

### 后端
- **框架**: FastAPI + Python 3.10+
- **数据验证**: Pydantic
- **HTTP 客户端**: httpx 异步客户端（非阻塞 LLM 调用与流式响应）
- **配置管理**: python-dotenv

### 前端
- **技术栈**: HTML5 + CSS3 + Vanilla JavaScript（`index.html` + `static/css` + `static/js`）
- **UI 风格**: 深色终端/赛博朋克风格
- **状态管理**: localStorage + 内存状态

### AI 模型
- 兼容 OpenAI API 格式的任意大模型
- 支持流式响应（SSE）
- 自动重试机制（最多3次）
- JSON 响应解析与修复

### 数据存储
- **格式**: JSON + Markdown
- **结构**: 文件系统（按游戏 ID 隔离）
- **日志**: LLM 调用完整记录

### 包管理
- **工具**: uv
- **依赖**: 见 pyproject.toml

## 配置说明

### 环境变量（.env）
```
API_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
API_MODEL=ark-code-latest
API_KEY=你的API密钥
```

### Prompt 模板（app/config.py）
项目包含多个精心设计的 Prompt 模板：

- `SYSTEM_PROMPT` - 游戏叙述者系统提示（含倾向系统规则、关键抉择标记、关系变化输出格式）
- `MEMORY_UPDATE_PROMPT` - 记忆文档更新模板
- `NPC_DIALOGUE_PROMPT` - NPC 对话角色扮演模板（根据性格、关系生成对话）
- `PLAYER_GENERATION_PROMPT` - 主角生成模板
- `NPC_GENERATION_PROMPT` - NPC 生成模板
- `CHARACTER_GENERATION_PROMPT` - 通用角色生成模板
- `RELATION_GENERATION_PROMPT` - 角色关系生成模板
- `NOVEL_GENERATION_PROMPT` - 小说生成模板
- `NOVEL_CHAPTER_PROMPT` - 章节生成模板
- `STORY_EXPANSION_PROMPT` - 故事设定扩展模板

## 常见问题

### Q: 游戏进度会丢失吗？
A: 不会。游戏使用文件系统存储，每个游戏独立保存，支持多存档位。前端还有 localStorage 自动保存。

### Q: 如何重新开始游戏？
A: 点击"开始新游戏"会创建全新的游戏目录，与历史游戏完全隔离。

### Q: 小说生成需要多长时间？
A: 通常需要 2-5 分钟，具体取决于故事长度。生成过程中会显示实时进度。

### Q: 可以导出游戏记录吗？
A: 游戏记录保存在 `games/game_xxx/memory/memory.md` 文件中，可以直接查看或分享。

### Q: 如何切换不同的游戏？
A: 点击"游戏列表"按钮，可以查看、加载或删除历史游戏。

### Q: 支持哪些 AI 模型？
A: 支持任何兼容 OpenAI API 格式的大模型服务，包括火山引擎、OpenAI、Claude API 等。

### Q: 为什么 NPC 生成失败？
A: NPC 生成超时（180秒）时会继续游戏流程，不影响主线体验。可以稍后手动添加角色。

## 开发说明

### 环境要求
- Python 3.10 或更高版本
- uv 包管理器

### 本地开发
```bash
# 安装依赖（含开发组：pytest）
uv sync --all-groups

# 启动开发服务器（热重载）
uv run uvicorn server:app --host 0.0.0.0 --port 8080 --reload

# 访问应用
open http://localhost:8080
```

### 运行测试
```bash
uv sync --all-groups
uv run pytest tests/ -q
```

### Docker
```bash
docker compose up --build
# 浏览器访问 http://localhost:8080
# 通过环境变量或 shell 中的 API_BASE_URL / API_KEY / API_MODEL 配置模型
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

## 已知限制

1. **前端状态管理**: 使用内存状态，页面刷新会丢失未保存的进度
2. **并发限制**: 尽管后端已在诸如 NPC 批量生成中接入了 `asyncio.gather` 和网络连接池解决拥塞，但在处理巨量角色同时生成时，仍可能受限于 LLM 大模型提供商的并发速率限制（Rate Limit）。
3. **文件存储**: 不适合超大规模游戏数据，建议定期清理旧游戏
4. **LLM 响应**: 依赖外部 API，网络问题可能导致生成失败
5. **JSON 解析**: 部分模型可能返回格式不正确的 JSON，已有自动修复机制
6. **角色快照**: 需要手动触发创建，未自动按章节记录

## 未来改进方向

1. **数据库支持**: 迁移到 SQLite 或 PostgreSQL 提升查询性能
2. **WebSocket**: 实现实时流式响应，改善用户体验
3. **用户系统**: 添加多用户支持和权限管理
4. **导入导出**: 支持游戏数据打包导出和导入
5. **角色头像**: 集成 AI 图片生成 API 创建角色头像
6. **多语言**: 支持 English 等多语言界面
7. **移动端适配**: 优化移动设备交互体验
8. **剧情分支图**: 可视化展示故事走向和选择分支
9. **存档对比**: 显示不同存档点的差异对比
10. **自动快照**: 每轮游戏结束自动创建角色状态快照

## 更新日志

### v0.5.1 (2026-04-14)
- **代码质量与稳定性**
  - 规范异常捕获：将两处裸 `except:` 收窄为具体的 `json.JSONDecodeError`/`ValueError`，避免误吞 `KeyboardInterrupt` 等系统异常。
  - 日志规范迁移：所有业务层 `print` 调试输出统一迁移到 `logging`，便于生产环境分级管控。
  - HTTP 错误校验：前端 `apiFetch` 统一校验 `response.ok` 并抛出 `ApiError`，消除“错误页面解析导致静默失败”的盲区。
  - 错误处理架构：新增 `route_handler` 装饰器，消除路由层 60+ 处重复的 `try/except JSONResponse` 模板代码。
- **代码仓库治理**
  - 将 `.cursor/` 加入 `.gitignore`，避免 IDE 工作区意外推送到远程。
  - 移除已误提交的 IDE 计划文件，保持仓库纯净。

### v0.5.0 (2026-04-01)
- **架构并发优化**：破除单任务阻塞，引入 `httpx.AsyncClient` 全局复用池与 `asyncio.gather`，实现 NPC 等模块的安全高并发生成。
- **网关鲁棒重塑**：上线含指数退避（Exponential Backoff）重试机制的 LLM 网关层（`llm_gateway.py`），稳定抵御500/502等偶发网络瞬连波动。
- **存储操作加固**：整合目录防穿透（Path Traversal）安全组件与跨平台原子写入机制（`atomic_io`），杜绝极端竞态下本地游戏文件的数据破损危机。
- **代码除冗重构**：切除了堆砌缠绕、相互循环引用的多余 `llm_client.py` 模块，将 JSON 自愈引擎收敛规范至 `json_utils.py`，实现全面降本增效。
- **前端游玩修缮**：优化游戏交互反馈系统，修补读写游戏记录（存档名与422结构校验）时的崩溃白屏点，提升Modal关闭交互顺滑度。

### v0.4.0 (2025-03-27)
- 新增选择倾向系统：6对性格维度（勇敢/谨慎、善良/冷酷等），每个选项标注倾向标签，累积形成玩家性格画像
- 新增关键抉择机制：约每5轮出现命运转折点，以醒目样式标记
- 新增后果预览功能：高感知角色可看到选项后果提示
- 新增 NPC 实时对话系统：可直接与 NPC 角色扮演式对话，AI 基于角色性格和关系回应
- 新增关系变化反馈：选择涉及 NPC 时自动更新关系强度，日志面板实时显示关系变化
- 性格画像注入叙事：AI 叙述者根据玩家倾向数据调整剧情走向
- 代码质量优化：清理未使用的导入和冗余模型定义，修复 HTML 重复脚本加载

### v0.3.0 (2024-03-20)
- 重构游戏数据存储结构，实现完全数据隔离
- 新增游戏管理功能（创建、加载、删除、列表）
- 每个游戏独立存储角色、记忆、小说、存档
- 新增游戏列表界面，支持切换历史游戏
- 优化时间戳精度，确保游戏ID唯一性
- 添加数据迁移脚本和测试脚本
- 新增 LLM 调用日志记录功能
- 新增故事设定自动扩展功能

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
