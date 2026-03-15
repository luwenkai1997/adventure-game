# 生成小说功能实现计划

## 需求概述
游戏结束后显示【生成小说】按钮，点击后调用大模型API将游戏日志生成为小说（每轮日志=一章，每章约2000字），保存为Markdown格式到 `novels/novel-YYYYMMDD-HHMMSS/` 目录。

## 项目结构分析

### 现有文件
- `server.py` - FastAPI后端，处理游戏聊天API
- `index.html` - 前端页面，包含三个screen：start-screen、game-screen、ending-screen
- `.env` - 包含API配置（API_BASE_URL, API_MODEL, API_KEY）

### 游戏日志机制
- 前端通过 `logs` 数组存储每轮的 `log` 字段（一句话概括本章发生的事）
- 结局时前端跳转到 ending-screen

## 实现步骤

### 1. 后端实现 (server.py)

#### 1.1 新增生成小说API接口
- **接口路径**: `POST /api/generate-novel`
- **请求体**: `{"logs": ["第1章日志", "第2章日志", ...]}`
- **响应**: `{"novel_folder": "novels/novel-20260315-144700"}`

#### 1.2 大模型调用逻辑
- 构建小说生成prompt，包含：
  - 系统prompt说明任务要求
  - 每章日志作为章节大纲
  - 要求每章约2000字
  - 输出Markdown格式
- 调用大模型API生成内容

#### 1.3 文件系统操作
- 生成文件夹路径：`novels/novel-{日期时间}/`
- 创建目录
- 将生成的Markdown小说保存为 `novel.md`

### 2. 前端实现 (index.html)

#### 2.1 ending-screen添加生成小说按钮
- 在【重新开始】按钮旁边添加【生成小说】按钮

#### 2.2 前端JavaScript逻辑
- 保存logs到全局变量（结局时）
- 点击【生成小说】调用API `/api/generate-novel`
- 显示加载状态
- 显示生成结果/错误信息

## Prompt设计

### 小说生成Prompt
```
你是一个专业的小说作家。请根据以下游戏冒险日志，将其改编成一本完整的小说。

要求：
1. 每一章对应一个日志条目
2. 每章约2000字
3. 使用生动的描写和流畅的叙事
4. 保持原文的核心剧情和人物选择
5. 输出Markdown格式，每个章节用 ## 标题 标记

日志内容：
{每轮日志内容}

请开始创作：
```

## 文件结构
```
adventure-game/
├── server.py          (修改)
├── index.html         (修改)
├── .env
└── novels/            (新增，生成时创建)
    └── novel-20260315-144700/
        └── novel.md
```

## 实现顺序
1. 先修改后端 `server.py` - 添加生成小说API
2. 修改前端 `index.html` - 添加按钮和调用逻辑
3. 测试完整流程
