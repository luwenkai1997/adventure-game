# 文字冒险游戏

一个基于 AI 的沉浸式文字冒险游戏，支持自定义世界观，通过选择推动剧情发展。

## 功能特点

- 自定义世界观设定（赛博朋克、古代江湖、末日废土等）
- AI 动态生成剧情和选项
- 多种结局（好结局/坏结局/中立结局）
- 深色终端风格界面
- **智能剧情记录** - 自动更新 memory.md 记录故事发展
- **第4个自定义选项** - 可以自由输入故事发展方向
- **选择结局类型** - 结束游戏时可指定结局类型
- **右侧日志面板** - 实时显示每轮故事发展
- **游戏进度自动保存** - 使用 localStorage 持久化，刷新不丢失
- **小说生成** - 游戏结束后一键生成约10000字完整小说
- **实时进度反馈** - 小说生成过程显示进度和预计时间

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
├── server.py          # FastAPI 后端服务器
├── index.html         # 前端游戏页面
├── pyproject.toml     # 项目依赖配置
├── .env               # API 配置（本地，不上传）
├── .env.example       # 示例配置文件
├── .gitignore        # Git 忽略规则
├── memory/            # 游戏记忆文档（自动生成）
├── novels/           # 生成的小说（自动生成）
└── README.md         # 项目说明
```

## 游戏玩法

1. 在开始页输入你想探索的世界观描述
2. 点击"开始冒险"进入游戏
3. 阅读剧情，从三个预设选项中做出选择
4. 也可以输入自定义选项推进故事
5. 可随时点击"结束游戏"选择结局类型
6. 游戏进度会自动保存到浏览器，刷新页面不会丢失
7. 游戏结束后点击"生成小说"，系统会根据记忆文档创作完整小说
8. 小说生成过程会显示实时进度，完成后自动保存到 `novels/` 目录

## 技术架构

- **后端**: FastAPI + Python 3.10+
- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **AI模型**: DeepSeek API
- **数据存储**: memory.md (游戏记忆) + localStorage (前端持久化)
- **包管理**: uv

## 项目结构

```
adventure-game/
├── server.py          # FastAPI 后端服务器
├── index.html         # 前端游戏页面（包含HTML、CSS、JS）
├── pyproject.toml     # 项目依赖配置
├── .env               # API 配置（本地，不上传）
├── .env.example       # 示例配置文件
├── .gitignore         # Git 忽略规则
├── memory/            # 游戏记忆文档（自动生成）
│   └── memory.md      # 游戏状态和故事流程
├── novels/            # 生成的小说（自动生成）
│   └── novel-{timestamp}/
│       └── novel.md   # 完整小说内容
└── README.md          # 项目说明
```

## API 接口

### POST /api/chat
生成游戏剧情和选项

**请求体**:
```json
{
  "messages": [
    {"role": "user", "content": "开始游戏。世界观设定：..."}
  ],
  "extraPrompt": "",
  "endingType": ""
}
```

**响应**:
```json
{
  "content": "{\"scene\": \"剧情描述\", \"choices\": [\"选项A\", \"选项B\", \"选项C\"], \"log\": \"本章概要\"}"
}
```

### POST /api/save-memory
保存初始世界观到 memory.md

**请求体**:
```json
{
  "worldSetting": "赛博朋克新加坡",
  "storySummary": ""
}
```

### POST /api/update-memory
更新游戏记忆文档

**请求体**:
```json
{
  "scene": "场景描述",
  "selectedChoice": "玩家选择",
  "logSummary": "本章概要",
  "endingType": ""
}
```

### POST /api/generate-novel
根据记忆文档生成完整小说

**响应**:
```json
{
  "novel_folder": "novel-20240317-143022",
  "novel_path": "/path/to/novels/novel-20240317-143022/novel.md",
  "novel_content": "# 小说标题\n## 第一章\n..."
}
```

## 常见问题

### Q: 游戏进度会丢失吗？
A: 不会。游戏使用 localStorage 自动保存进度，即使刷新页面或关闭浏览器，下次打开时可以继续游戏。

### Q: 如何重新开始游戏？
A: 点击"重新开始"按钮即可开始新的游戏，旧的游戏记录会被清除。

### Q: 小说生成需要多长时间？
A: 通常需要 2-5 分钟，具体取决于故事长度。生成过程中会显示实时进度和预计剩余时间。

### Q: 可以导出游戏记录吗？
A: 游戏记录保存在 `memory/memory.md` 文件中，可以直接查看或分享。

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

### 配置说明
编辑 `.env` 文件配置 API：
```
API_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
API_MODEL=ark-code-latest
API_KEY=your_api_key_here
```

## 更新日志

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
