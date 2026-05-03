"""
QPred Bot · 配置 & AI 测试面板
- 浏览器访问后, 填入 BOT_TOKEN / Tokenhot Key / 模型 → 一键写入 .env
- 在线调用 tokenhot.ai 测试推理是否调通
- 一键启动 / 停止 Bot 进程
"""
import os
import sys
import json
import signal
import subprocess
from pathlib import Path

import httpx
from flask import Flask, render_template, request, jsonify

# 项目根目录 = web 的上一级
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"
PID_FILE = BASE_DIR / "data" / "bot.pid"
LOG_FILE = BASE_DIR / "logs" / "bot_runtime.log"

app = Flask(__name__, template_folder="templates", static_folder="static")

DEFAULT_BASE_URL = "https://api.tokenhot.ai/v1"
DEFAULT_MODEL = "claude-sonnet-4-6"

# Tokenhot 推荐模型清单 (用于下拉)
RECOMMEND_MODELS = [
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (推荐 · 性价比之王)"},
    {"id": "claude-opus-4-6", "name": "Claude Opus 4.6 (顶级综合)"},
    {"id": "claude-opus-4-6-thinking", "name": "Claude Opus 4.6 Thinking (深度推理)"},
    {"id": "gpt-5.4", "name": "GPT-5.4"},
    {"id": "gpt-5.2-high", "name": "GPT-5.2 High (OpenAI 最强)"},
    {"id": "gpt-5.4-nano", "name": "GPT-5.4 Nano (省钱)"},
    {"id": "o3", "name": "O3 (OpenAI 推理)"},
    {"id": "gemini-3-pro", "name": "Gemini 3 Pro"},
    {"id": "gemini-3-flash", "name": "Gemini 3 Flash (快速)"},
    {"id": "deepseek-v3.2", "name": "DeepSeek V3.2 (国产强)"},
    {"id": "grok-4.1-thinking", "name": "Grok 4.1 Thinking"},
]


# -------------------- .env 读写 --------------------

def parse_env(text: str) -> dict:
    data = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def load_env() -> dict:
    if ENV_FILE.exists():
        return parse_env(ENV_FILE.read_text(encoding="utf-8"))
    if ENV_EXAMPLE.exists():
        return parse_env(ENV_EXAMPLE.read_text(encoding="utf-8"))
    return {}


def save_env(updates: dict):
    """保留原文件注释 / 顺序, 仅替换变更项"""
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    elif ENV_EXAMPLE.exists():
        lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    seen = set()
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        k = stripped.split("=", 1)[0].strip()
        if k in updates:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
        else:
            out.append(line)

    # 新增未存在的键
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")

    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


# -------------------- 路由: 页面 --------------------

@app.route("/")
def index():
    env = load_env()
    return render_template(
        "index.html",
        env=env,
        models=RECOMMEND_MODELS,
        default_base_url=DEFAULT_BASE_URL,
        default_model=DEFAULT_MODEL,
        bot_running=is_bot_running(),
    )


# -------------------- 路由: 保存配置 --------------------

@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.json or {}
    updates = {
        "BOT_TOKEN": data.get("bot_token", "").strip(),
        "ADMIN_IDS": data.get("admin_ids", "").strip(),
        "GROUP_CHAT_ID": data.get("group_chat_id", "0").strip() or "0",
        "AI_PROVIDER": "tokenhot",
        "OPENAI_API_KEY": data.get("api_key", "").strip(),
        "OPENAI_BASE_URL": data.get("base_url", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
        "OPENAI_MODEL": data.get("model", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "ENABLE_AI": "true",
        "ENABLE_RAG": "true" if data.get("enable_rag", True) else "false",
        "REPLY_ALL_GROUP_MESSAGES": "true" if data.get("reply_all", True) else "false",
        "QPRED_API_BASE": data.get("qpred_api_base", "https://api.qpred.io").strip(),
        "QPRED_WEBSITE": data.get("qpred_website", "https://www.qpred.io").strip(),
    }
    try:
        save_env(updates)
        return jsonify({"ok": True, "msg": "✅ 配置已保存到 .env"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"❌ 保存失败: {e}"})


# -------------------- 路由: 测试 AI --------------------

@app.route("/api/test_ai", methods=["POST"])
def api_test_ai():
    """直接 POST 到 tokenhot.ai 验证 Key + 模型"""
    data = request.json or {}
    api_key = data.get("api_key", "").strip()
    base_url = (data.get("base_url") or DEFAULT_BASE_URL).strip()
    model = (data.get("model") or DEFAULT_MODEL).strip()
    question = data.get("question", "你好, 请用一句话介绍 QPred 平台").strip()

    if not api_key:
        return jsonify({"ok": False, "msg": "❌ 请先填写 Tokenhot API Key"})

    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "你是 QPred (qpred.io) 的官方 AI 客服, "
                "回答精炼、专业、不超过 200 字。"
            )},
            {"role": "user", "content": question},
        ],
        "temperature": 0.4,
        "max_tokens": 400,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code != 200:
            return jsonify({
                "ok": False,
                "msg": f"❌ HTTP {r.status_code}: {r.text[:500]}",
            })
        body = r.json()
        answer = (
            body.get("choices", [{}])[0].get("message", {}).get("content", "")
            or json.dumps(body, ensure_ascii=False)[:500]
        )
        usage = body.get("usage", {})
        return jsonify({
            "ok": True,
            "answer": answer.strip(),
            "model": body.get("model", model),
            "usage": usage,
        })
    except Exception as e:
        return jsonify({"ok": False, "msg": f"❌ 调用异常: {type(e).__name__}: {e}"})


# -------------------- 路由: 测试 BOT_TOKEN --------------------

@app.route("/api/test_bot", methods=["POST"])
def api_test_bot():
    data = request.json or {}
    token = data.get("bot_token", "").strip()
    if not token:
        return jsonify({"ok": False, "msg": "❌ 请先填写 BOT_TOKEN"})
    try:
        r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        body = r.json()
        if body.get("ok"):
            info = body["result"]
            return jsonify({
                "ok": True,
                "msg": (
                    f"✅ Bot 连接成功!\n"
                    f"名称: {info.get('first_name')}\n"
                    f"用户名: @{info.get('username')}\n"
                    f"ID: {info.get('id')}"
                ),
            })
        return jsonify({"ok": False, "msg": f"❌ Telegram 返回: {body}"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"❌ 网络错误: {e}"})


# -------------------- 路由: 启动 / 停止 / 状态 --------------------

def is_bot_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False


@app.route("/api/bot/start", methods=["POST"])
def api_bot_start():
    if is_bot_running():
        return jsonify({"ok": True, "msg": "Bot 已在运行"})
    if not ENV_FILE.exists():
        return jsonify({"ok": False, "msg": "❌ 请先保存配置 (.env 不存在)"})
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_fp = open(LOG_FILE, "ab")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(BASE_DIR),
        stdout=log_fp,
        stderr=log_fp,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))
    return jsonify({"ok": True, "msg": f"🚀 Bot 已启动 (PID={proc.pid})"})


@app.route("/api/bot/stop", methods=["POST"])
def api_bot_stop():
    if not is_bot_running():
        return jsonify({"ok": True, "msg": "Bot 未运行"})
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        return jsonify({"ok": True, "msg": f"🛑 已停止 Bot (PID={pid})"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"停止失败: {e}"})


@app.route("/api/bot/status", methods=["GET"])
def api_bot_status():
    log_tail = ""
    if LOG_FILE.exists():
        try:
            data = LOG_FILE.read_bytes()[-4096:]
            log_tail = data.decode("utf-8", errors="ignore")
        except Exception:
            pass
    return jsonify({
        "running": is_bot_running(),
        "log_tail": log_tail,
    })


if __name__ == "__main__":
    port = int(os.getenv("PANEL_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
