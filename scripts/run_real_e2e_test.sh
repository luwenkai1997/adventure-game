#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "🔥 启动带有真实依赖的测试服务器 (Port: 8000)..."
# 后台启动独立的真实服务器实例
uv run uvicorn server:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
SERVER_PID=$!

function cleanup {
  echo "♻️ 正在销毁临时后台测试服务器进程 $SERVER_PID"
  kill $SERVER_PID || true
}
trap cleanup EXIT

# 等待 FastAPI Uvicorn 服务完全启动
sleep 3

echo "🕵️ 开始执行无 Mock 全真 E2E Playwright 推演脚本"
export REAL_E2E=1

# -s 保持标准输出，--headed 开启可见的弹窗浏览器模式以符合可视化预期
uv run pytest tests/e2e/test_real_flow.py -v -s --headed
