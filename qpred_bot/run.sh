#!/usr/bin/env bash
# QPred Telegram Bot 启动脚本
set -e

cd "$(dirname "$0")"

# 1. 创建虚拟环境 (首次)
if [ ! -d "venv" ]; then
  echo "📦 Creating venv..."
  python3 -m venv venv
fi

# 2. 激活
source venv/bin/activate

# 3. 安装依赖
pip install -q -r requirements.txt

# 4. 检查 .env
if [ ! -f ".env" ]; then
  echo "⚠️  .env 不存在, 从 .env.example 复制"
  cp .env.example .env
  echo "请先编辑 .env 填入 BOT_TOKEN / OPENAI_API_KEY 等, 再重新执行 ./run.sh"
  exit 1
fi

# 5. 启动
echo "🚀 Starting QPred Bot..."
exec python main.py
