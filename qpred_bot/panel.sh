#!/usr/bin/env bash
# QPred Bot · 启动 Web 配置面板
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "⚠️  请先执行 ./setup.sh 安装依赖"
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate

PORT="${PANEL_PORT:-8080}"
echo "=========================================="
echo " 🎛  QPred Bot 配置面板"
echo "=========================================="
echo " 浏览器打开: http://localhost:${PORT}"
echo " 按 Ctrl+C 退出"
echo "=========================================="

cd web && PANEL_PORT="$PORT" python app.py
