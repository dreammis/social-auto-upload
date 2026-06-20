#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "🔍 Checking Python environment..."
if ! command -v uv &>/dev/null; then
  echo "❌ 'uv' is not installed. Please install it first:"
  echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

echo "📦 Creating virtual environment (.venv) if needed..."
if [ ! -d ".venv" ]; then
  uv venv
  echo "✅ Virtual environment created."
else
  echo "✅ Virtual environment already exists."
fi

echo "📥 Installing project dependencies (this may take a minute)..."
source .venv/bin/activate
uv pip install -e .
uv pip install -e ".[web]"

echo "🌐 Installing patchright Chromium browser..."
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium

echo "🚀 Starting server at http://localhost:5409 ..."
echo "   Open this URL in your browser to use the app."
echo "   Press Ctrl+C to stop."
echo ""
python web_runner.py
