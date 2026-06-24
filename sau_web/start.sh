#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$(realpath "$0")")/.." && pwd)"
LOG_DIR="$ROOT/.sau-logs"
mkdir -p "$LOG_DIR"

fail() { echo "[ERROR] $*" >&2; exit 1; }

cleanup() {
  echo "[stop] stopping services..."
  [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  echo "[stop] done"
}
trap cleanup EXIT INT TERM

kill_port() {
  local port="$1"
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  fi
  if [ -n "$pids" ]; then
    echo "[stop] closing port $port (pids: $pids)"
    kill $pids >/dev/null 2>&1 || true
    sleep 1
  fi
}

# Find python executable — prefer .venv
PYTHON=""
if [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
fi
[ -z "$PYTHON" ] && fail "python not found"
echo "[info] using $PYTHON"

# 1) 检查/安装 Python 依赖（Flask 壳）
if ! "$PYTHON" -c "import flask" >/dev/null 2>&1; then
  echo "[setup] install web deps"
  cd "$ROOT"
  if command -v uv >/dev/null 2>&1; then
    uv pip install -e ".[web]"
  else
    pip install -e ".[web]"
  fi
fi

# 2) 检查/安装前端依赖
if [ ! -d "$ROOT/sau_web/frontend/node_modules" ]; then
  echo "[setup] install frontend deps"
  cd "$ROOT/sau_web/frontend"
  npm install
fi

# 3) 关闭默认端口，再启动
kill_port 6001
kill_port 5174

# 4) 启动后端
echo "[start] backend -> http://localhost:6001"
cd "$ROOT"
export SAU_CORS_ALLOWED_ORIGINS="${SAU_CORS_ALLOWED_ORIGINS:-http://localhost:5173,http://localhost:5174}"
"$PYTHON" run.py > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "[start] backend pid=$BACKEND_PID"

# 5) 启动前端
echo "[start] frontend -> http://localhost:5174"
cd "$ROOT/sau_web/frontend"
npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "[start] frontend pid=$FRONTEND_PID"

echo
echo "前端: http://localhost:5174"
echo "后端: http://localhost:6001"
echo "日志: $LOG_DIR"
echo
echo "停止: Ctrl+C 或 wait"
wait
