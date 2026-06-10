#!/usr/bin/env bash
# 启动后端（开发模式，热重载）
# 用法: 在项目根目录执行  ./scripts/run_backend_dev.sh
# 与 run_frontend_dev 分开两个终端跑；dev 模式下 Tauri 不拉起 sidecar，
# 后端由本脚本启动，避免抢 5409 端口。
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 优先 flask --debug 自动 reload；没有 flask CLI 时回退 python sau_backend.py
if command -v flask >/dev/null 2>&1; then
    FLASK_APP=sau_backend flask --app sau_backend --debug run --host 0.0.0.0 --port 5409
else
    echo "flask CLI 不可用，回退 python sau_backend.py"
    python sau_backend.py
fi
