# 功能优化行动计划

## 版本管理策略

### Git分支结构
```
main                    # 生产环境稳定代码
├── develop             # 开发主分支
│   ├── feature/player-attributes      # 阶段1：玩家属性系统
│   ├── feature/dice-check             # 阶段2：骰子检定系统
│   └── feature/save-load              # 阶段3：存档/回退功能
└── releases/          # 版本发布
```

### 版本号规划
- 当前版本：v0.1.0
- 新版本：v0.2.0（包含所有新功能）
- 采用语义化版本：主版本.次版本.修订号

### 提交规范
- feat: 新功能
- fix: 修复bug
- refactor: 重构
- docs: 文档
- test: 测试
- chore: 构建/工具

---

## 阶段1：玩家属性/技能系统

### 1.1 新增文件

**`app/models/player.py`** - 玩家数据模型
```python
# 核心类
class PlayerCharacter(BaseModel)
class PlayerSkill(BaseModel)
class PlayerCreateRequest(BaseModel)
class PlayerRandomRequest(BaseModel)

# 预设数据
PRESET_SKILLS = {
    "combat": ["剑术", "箭术", "格斗", "双持", "防御"],
    "social": ["说服", "恐吓", "欺骗", "表演", "察言观色"],
    "knowledge": ["魔法学识", "历史", "草药", "炼金", "符文"],
    "survival": ["潜行", "追踪", "野外生存", "急救", "开锁"]
}
```

**`app/services/player_service.py`** - 玩家服务逻辑
```python
class PlayerService:
    def create_player() -> PlayerCharacter
    def random_player() -> PlayerCharacter
    def get_player() -> PlayerCharacter
    def update_player() -> PlayerCharacter
    def calculate_modifier(attribute: int) -> int  # 属性修正计算
```

**`app/api/player_routes.py`** - 玩家API路由
```
POST   /api/player/create     - 创建玩家角色
POST   /api/player/random     - 随机生成玩家
GET    /api/player/get        - 获取玩家信息
PUT    /api/player/update     - 更新玩家属性
```

**`data/player/`** - 玩家数据目录
- `player.json` - 当前玩家角色数据

### 1.2 修改文件

**`app/config.py`** - 新增配置
```python
# 新增目录配置
PLAYER_DIR = os.path.join(DATA_DIR, 'player')

# 新增预设技能配置
PRESET_SKILLS_CN = {...}
ATTRIBUTE_NAMES_CN = {...}
```

**`app/models/__init__.py`** - 导出新模型
```python
from app.models.player import PlayerCharacter, PlayerSkill, ...
```

**`server.py`** - 注册新路由
```python
from app.api.player_routes import router as player_router
app.include_router(player_router)
```

**`app/utils/file_storage.py`** - 新增存储函数
```python
def get_or_create_player_dir()
def save_player(player: dict) -> str
def load_player() -> Optional[dict]
def delete_player() -> bool
```

### 1.3 前端修改（index.html）

**新增页面**：
```html
<!-- 角色创建界面 -->
<div id="character-creation-screen" class="screen">
    <!-- 基础信息表单 -->
    <!-- 属性分配区域（6个滑块） -->
    <!-- 技能选择区域 -->
    <!-- 随机/自定义切换 -->
    <!-- 预览面板 -->
</div>
```

**新增CSS**：
```css
.character-creation-screen { }
.attribute-slider { }
.skill-selector { }
.random-btn { }
```

**新增JavaScript**：
```javascript
// 状态变量
let playerCharacter = null;
let attributePoints = 20;

// 函数
function showCharacterCreation()
function randomCharacter()
function updateAttributeSlider()
function selectSkill()
function validateCharacterCreation()
function createPlayer()
function loadPlayerPanel()
```

**修改现有代码**：
- 开始页面添加"创建角色"按钮
- 游戏界面添加玩家属性面板（可折叠）
- 游戏开始前必须创建角色

### 1.4 测试计划
```bash
# 单元测试
pytest tests/test_player_service.py
pytest tests/test_player_model.py

# API测试
curl -X POST http://localhost:8080/api/player/random
curl -X GET http://localhost:8080/api/player/get
```

---

## 阶段2：骰子检定系统

### 2.1 新增文件

**`app/services/check_service.py`** - 检定服务
```python
class CheckService:
    def roll_d20() -> int
    def calculate_modifier(attribute: int) -> int
    def perform_check(
        attribute: str,
        skill: str,
        difficulty: int
    ) -> CheckResult
    
    def get_difficulty_name(dc: int) -> str
    def get_difficulty_color(dc: int) -> str
```

**`app/models/check.py`** - 检定数据模型
```python
class CheckRequest(BaseModel)
class CheckResult(BaseModel)

# 难度等级常量
DIFFICULTY_EASY = 8      # 简单
DIFFICULTY_AVERAGE = 12   # 普通
DIFFICULTY_HARD = 16     # 困难
DIFFICULTY_VERY_HARD = 20  # 极难
DIFFICULTY_NEAR_IMPOSSIBLE = 25  # 几乎不可能
```

**`app/api/check_routes.py`** - 检定API路由
```
POST /api/check - 执行骰子检定
```

### 2.2 修改文件

**`app/config.py`** - 新增提示词
```python
# 修改 SYSTEM_PROMPT
DICE_CHECK_SYSTEM_PROMPT = """
...
请根据玩家属性和技能，为某些选项添加检定信息...
"""

# 新增检定结果提示词
CHECK_RESULT_PROMPT = """
检定失败剧情生成...
"""
```

**`app/services/game_service.py`** - 新增检定逻辑
```python
def parse_check_from_choice(choice: dict) -> Optional[dict]
def should_include_check(scene: str, player_stats: dict) -> bool
```

**`app/api/game_routes.py`** - 修改chat接口
```python
# 修改 /api/chat
# 请求增加 player_id 参数
# 返回增加 check_info 字段
```

### 2.3 前端修改（index.html）

**新增UI元素**：
```html
<!-- 骰子检定弹窗 -->
<div id="check-modal" class="modal">
    <div class="dice-container">
        <div class="dice">?</div>
        <div class="modifier">+5</div>
        <div class="vs">VS</div>
        <div class="difficulty">DC 15</div>
    </div>
    <div class="check-result"></div>
</div>

<!-- 属性面板显示 -->
<div id="player-panel" class="panel">
    <div class="attributes">...</div>
    <div class="skills">...</div>
</div>
```

**新增CSS**：
```css
.dice-container { }
.dice { animation: roll; }
.check-success { color: green; }
.check-failure { color: red; }
```

**新增JavaScript**：
```javascript
// 状态变量
let currentCheck = null;

// 函数
function performDiceCheck(attribute, skill, difficulty)
function animateDiceRoll(finalValue)
function showCheckResult(success, narrative)
function applyCheckEffect(narrative)
```

### 2.4 测试计划
```bash
# 测试随机数分布
pytest tests/test_check_service.py -v

# 测试API
curl -X POST http://localhost:8080/api/check \
  -H "Content-Type: application/json" \
  -d '{"attribute": "strength", "skill": "剑术", "difficulty": 15}'
```

---

## 阶段3：存档/读档 + 回退功能

### 3.1 新增文件

**`app/models/save.py`** - 存档数据模型
```python
class GameSave(BaseModel)
class HistorySnapshot(BaseModel)
class SaveListResponse(BaseModel)
class SaveDetailResponse(BaseModel)
```

**`app/services/save_service.py`** - 存档服务
```python
class SaveService:
    # 存档管理
    def list_saves() -> List[SaveSummary]
    def get_save(slot_id: str) -> GameSave
    def save_game(slot_id: str, save_data: dict) -> GameSave
    def delete_save(slot_id: str) -> bool
    def load_save(slot_id: str) -> dict
    
    # 回退管理
    def push_history(snapshot: HistorySnapshot)
    def undo() -> Optional[HistorySnapshot]
    def get_history() -> List[HistorySnapshot]
    def clear_history()
```

**`app/api/save_routes.py`** - 存档API路由
```
GET    /api/save/list              - 获取存档列表
GET    /api/save/{slot_id}         - 获取存档详情
POST   /api/save/{slot_id}         - 保存游戏
DELETE /api/save/{slot_id}         - 删除存档
POST   /api/save/load/{slot_id}    - 加载存档

GET    /api/history                - 获取回退历史
POST   /api/history/undo           - 回退一步
DELETE /api/history                - 清空回退历史
```

**`data/saves/`** - 存档目录
```
save_1.json
save_2.json
save_3.json
save_4.json
save_5.json
history.json
```

### 3.2 修改文件

**`app/config.py`** - 新增配置
```python
SAVES_DIR = os.path.join(DATA_DIR, 'saves')
MAX_SAVE_SLOTS = 5
MAX_HISTORY_STEPS = 10
```

**`app/utils/file_storage.py`** - 新增存档函数
```python
def get_or_create_saves_dir()
def save_game_state(slot_id: str, data: dict) -> str
def load_game_state(slot_id: str) -> Optional[dict]
def list_saves() -> List[dict]
def delete_game_save(slot_id: str) -> bool
def save_history(history: List[dict])
def load_history() -> List[dict]
```

### 3.3 前端修改（index.html）

**新增UI元素**：
```html
<!-- 存档界面 -->
<div id="save-screen" class="screen">
    <div class="save-slots">
        <div class="save-slot" data-slot="1">
            <div class="slot-name">存档 1</div>
            <div class="slot-info">章节: 3 | 世界观: 古代江湖</div>
            <div class="slot-time">2024-03-19 10:30</div>
            <div class="slot-actions">
                <button onclick="loadSave(1)">加载</button>
                <button onclick="overwriteSave(1)">覆盖</button>
                <button onclick="deleteSave(1)">删除</button>
            </div>
        </div>
        <!-- 更多存档位 -->
    </div>
</div>

<!-- 回退按钮 -->
<button id="undo-btn" class="btn btn-icon" title="回退一步">
    ↩️ <span id="undo-count">0</span>
</button>

<!-- 存档/读档按钮 -->
<div class="game-actions">
    <button onclick="showSaveScreen()">存档</button>
    <button onclick="showLoadScreen()">读档</button>
</div>
```

**新增JavaScript**：
```javascript
// 状态变量
let saveSlots = [];
let historyStack = [];
let canUndo = false;

// 存档相关函数
function showSaveScreen()
function showLoadScreen()
function saveGame(slotId)
function loadGame(slotId)
function deleteSave(slotId)
function updateSaveSlots()

// 回退相关函数
function undo()
function pushHistory()
function updateUndoButton()
```

### 3.4 测试计划
```bash
# 测试存档功能
curl -X POST http://localhost:8080/api/save/1 \
  -H "Content-Type: application/json" \
  -d '{"save_name": "测试存档", ...}'

curl -X GET http://localhost:8080/api/save/list

# 测试回退功能
curl -X POST http://localhost:8080/api/history/undo
```

---

## 实施顺序和时间规划

### 第1天：准备工作
- [ ] 创建Git分支
- [ ] 备份现有代码
- [ ] 搭建测试环境

### 第2-3天：阶段1（玩家属性系统）
- [ ] 创建数据模型
- [ ] 创建API路由
- [ ] 创建服务层
- [ ] 前端角色创建界面
- [ ] 单元测试

### 第4-5天：阶段2（骰子检定系统）
- [ ] 创建检定服务
- [ ] 修改AI提示词
- [ ] 前端检定UI
- [ ] 集成测试

### 第6-7天：阶段3（存档/回退系统）
- [ ] 创建存档模型和服务
- [ ] 创建存档API
- [ ] 前端存档/读档界面
- [ ] 回退功能实现
- [ ] 集成测试

### 第8天：收尾
- [ ] 代码审查
- [ ] 文档更新
- [ ] 版本发布

---

## 代码质量保障

### Lint和格式化
```bash
# Python代码检查
uv run ruff check app/

# 自动修复
uv run ruff check --fix app/

# 格式化代码
uv run ruff format app/
```

### 测试覆盖
```bash
# 运行所有测试
uv run pytest tests/

# 生成覆盖率报告
uv run pytest --cov=app tests/
```

### Git提交检查
- 提交前运行lint
- 提交信息规范
- 代码审查流程

---

## 回滚方案

### 如果某个阶段出现问题：
1. 切换到上一个稳定分支
2. 分析问题原因
3. 修复后重新合并

### 版本回退：
```bash
git revert <commit_hash>
git push origin main
```

---

## 部署流程

### 1. 开发环境
```bash
uv sync
uv run uvicorn server:app --reload
```

### 2. 测试环境
```bash
git checkout develop
# 部署测试版本
```

### 3. 生产环境
```bash
git checkout main
git merge develop
git tag v0.2.0
git push origin main --tags
```
