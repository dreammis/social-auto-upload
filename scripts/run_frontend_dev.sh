#!/usr/bin/env bash
# 启动前端 + Tauri 桌面窗口（开发模式，Vue HMR 热更新）
# 用法: 在项目根目录执行  ./scripts/run_frontend_dev.sh
# dev 模式下不拉起 sidecar，后端请另开终端跑 run_backend_dev.sh。
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT/sau_frontend"

npm run tauri dev
