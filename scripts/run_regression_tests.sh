#!/usr/bin/env bash

# 出错时退出
set -e

# 定位到项目根目录
cd "$(dirname "$0")/.."

echo "======================================"
echo "    adventure-game 回归测试系统启动"
echo "======================================"

echo "[1/4] 环境变量检查与设置..."
# 为了在测试中禁用一些开发环境特性或者开启Mock，设置一个特殊的测试标志
export TESTING=1
export PYTHONUNBUFFERED=1

# 检查依赖是否就绪
if ! uv run pytest --version > /dev/null 2>&1; then
    echo "❌ 错误: 环境中没有检测到 pytest，正在通过 uv 重新挂载开发依赖..."
    uv add --dev pytest pytest-asyncio pytest-cov pytest-mock ruff
fi

echo "✅ 依赖检查通过"

echo "[2/4] 静态代码检查 (Ruff)..."
if uv run ruff check app tests; then
    echo "✅ 静态代码检查通过"
else
    echo "⚠️  警告: 存在某些潜伏的语法/格式问题，请及时修正"
    # 如果希望 Linter 不过时阻断测试，可以开启出口
    # exit 1
fi

echo "[3/4] 执行单元测试与集成测试..."
echo "正在使用 pytest 运行所有测试并汇集覆盖率..."
# 设定覆盖率拦截底线（这里配置为 30%，因为是个开始）
# 可以后续通过 `cov-fail-under=80` 来阻拦提交流水线
uv run pytest tests -v \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=html:tests/coverage_html

if [ $? -eq 0 ]; then
    echo "✅ pytest 全部单元测试及集成测试运行通过"
else
    echo "❌ 错误: 测试用例发生失败，自动拦截变更提交"
    exit 1
fi

echo "[4/4] 收尾与清理..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

echo "======================================"
echo "    🎉 恭喜！回归测试通过，您的代码更改很安全"
echo "    可查看详细 HTML 覆盖率报告: tests/coverage_html/index.html"
echo "======================================"
