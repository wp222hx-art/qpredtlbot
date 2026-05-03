"""
QPred Bot 配置中心
- 多供应商 AI 模型配置 (OpenAI / DeepSeek / OpenRouter / 自定义兼容端点)
- 群管 / 反诈 / 反刷屏 / 白名单
"""
import os
from dotenv import load_dotenv

load_dotenv()


# 默认走 Tokenhot 统一网关 (OpenAI 兼容协议)
TOKENHOT_BASE_URL = "https://api.tokenhot.ai/v1"

# 供应商别名 → BASE_URL (全部通过 tokenhot 网关访问, 无需单独申请 Key)
PROVIDER_BASE_URLS = {
    "tokenhot": TOKENHOT_BASE_URL,
    "openai": TOKENHOT_BASE_URL,
    "anthropic": TOKENHOT_BASE_URL,
    "claude": TOKENHOT_BASE_URL,
    "gemini": TOKENHOT_BASE_URL,
    "deepseek": TOKENHOT_BASE_URL,
    "grok": TOKENHOT_BASE_URL,
    "qwen": TOKENHOT_BASE_URL,
    "custom": "",
}

# Tokenhot 推荐模型 (按场景)
TOKENHOT_MODELS = {
    "性价比": "gpt-5.4-nano",
    "核心": "claude-sonnet-4-6",
    "推理强者": "o3",
    "顶级": "claude-opus-4-6",
    "国产强者": "deepseek-v3.2",
    "Gemini": "gemini-3-flash",
}


class Config:
    # ===== Telegram =====
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS = [
        int(x.strip())
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().lstrip("-").isdigit()
    ]
    GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0") or "0")

    # ===== AI 推理 (默认走 tokenhot.ai 网关) =====
    AI_PROVIDER = os.getenv("AI_PROVIDER", "tokenhot").lower().strip()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # 即 Tokenhot Key (sk-xxx)
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "claude-sonnet-4-6")
    OPENAI_BASE_URL = (
        os.getenv("OPENAI_BASE_URL", "").strip()
        or PROVIDER_BASE_URLS.get(AI_PROVIDER, TOKENHOT_BASE_URL)
    )
    ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
    ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

    # 群里每条消息都自动回复? true=全员AI客服 / false=仅 @机器人/关键词触发
    REPLY_ALL_GROUP_MESSAGES = os.getenv("REPLY_ALL_GROUP_MESSAGES", "true").lower() == "true"

    # ===== QPred =====
    QPRED_API_BASE = os.getenv("QPRED_API_BASE", "https://api.qpred.io")
    QPRED_WEBSITE = os.getenv("QPRED_WEBSITE", "https://www.qpred.io")

    # ===== Database =====
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/qpred_bot.db")

    # ===== Logging =====
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "./logs/qpred_bot.log")

    # ===== Guardian =====
    ENABLE_GUARDIAN = os.getenv("ENABLE_GUARDIAN", "true").lower() == "true"
    ENABLE_CAPTCHA = os.getenv("ENABLE_CAPTCHA", "true").lower() == "true"
    CAPTCHA_TIMEOUT = int(os.getenv("CAPTCHA_TIMEOUT", "60"))
    ANTI_FLOOD_WINDOW = int(os.getenv("ANTI_FLOOD_WINDOW", "10"))
    ANTI_FLOOD_MAX = int(os.getenv("ANTI_FLOOD_MAX", "5"))

    # ===== 定时广播 =====
    BROADCAST_MARKETS_INTERVAL = int(os.getenv("BROADCAST_MARKETS_INTERVAL", "120"))
    BROADCAST_PRICE_INTERVAL = int(os.getenv("BROADCAST_PRICE_INTERVAL", "60"))

    # 白名单域名
    SAFE_DOMAINS = [
        "qpred.io", "www.qpred.io",
        "t.me/qpred", "twitter.com", "x.com",
        "github.com", "medium.com"
    ]

    # 反诈骗关键词
    SPAM_KEYWORDS = [
        r"私信.*?(客服|管理员|admin)",
        r"(空投|airdrop).*?(点击|链接|click here)",
        r"(保证|guaranteed).*?(收益|profit|\d+%)",
        r"联系.*?(微信|vx|wechat)",
        r"100%.*?(赚|win|profit)",
    ]

    @classmethod
    def validate(cls):
        """启动前校验"""
        errors = []
        if not cls.BOT_TOKEN:
            errors.append("❌ BOT_TOKEN 未配置")
        if not cls.ADMIN_IDS:
            errors.append("⚠️  ADMIN_IDS 未配置, 管理员命令将不可用")
        if cls.ENABLE_AI and not cls.OPENAI_API_KEY:
            errors.append("⚠️  ENABLE_AI=true 但 OPENAI_API_KEY 未配置")
        return errors


config = Config()
