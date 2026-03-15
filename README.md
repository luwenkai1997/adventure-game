# 文字冒险游戏

一个基于 AI 的沉浸式文字冒险游戏，支持自定义世界观，通过选择推动剧情发展。

## 功能特点

- 自定义世界观设定（赛博朋克、古代江湖、末日废土等）
- AI 动态生成剧情和选项
- 8 章完整故事线，多种结局
- 深色终端风格界面
- 冒险日志记录关键选择

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
├── .env               # API 配置（不上传）
├── .env.example       # 示例配置文件
├── .gitignore         # Git 忽略规则
└── README.md          # 项目说明
```

## 游戏玩法

1. 在开始页输入你想探索的世界观描述
2. 点击"开始冒险"进入游戏
3. 阅读剧情，从三个选项中做出选择
4. 你的选择将影响故事走向和最终结局
5. 第 8 章将迎来结局（好结局/中立结局/坏结局）
