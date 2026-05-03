#!/usr/bin/env bash
# QPred Bot · 一键安装脚本
set -e

cd "$(dirname "$0")"

echo "=========================================="
echo " 🤖 QPred Telegram Bot · 一键安装"
echo "=========================================="

# 1. Python 版本检查
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python 版本: $PY_VERSION"

# 2. 创建虚拟环境
if [ ! -d "venv" ]; then
  echo "📦 创建 venv..."
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
echo "✅ 虚拟环境已激活"

# 3. 安装依赖
echo "📦 安装依赖..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ 依赖安装完成"

# 4. 准备 .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "✅ 已生成 .env (从模板)"
fi

# 5. 创建数据 / 日志目录
mkdir -p data logs

echo ""
echo "=========================================="
echo " 🎉 安装完成! 接下来:"
echo "=========================================="
echo " 方式 A · 浏览器配置 (推荐):"
echo "    ./panel.sh"
echo "    打开 http://localhost:8080"
echo ""
echo " 方式 B · 命令行配置:"
echo "    vim .env   # 填 BOT_TOKEN / OPENAI_API_KEY"
echo "    python main.py"
echo "=========================================="
