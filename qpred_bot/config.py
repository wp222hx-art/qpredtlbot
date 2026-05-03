"""
QPred Bot 配置中心
- 多供应商 AI 模型配置 (OpenAI / DeepSeek / OpenRouter / 自定义兼容端点)
- 群管 / 反诈 / 反刷屏 / 白名单
"""
import os
from dotenv import load_dotenv

load_dotenv()


# 各供应商默认 BASE_URL
PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "custom": "",
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

    # ===== AI 推理 =====
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower().strip()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL = (
        os.getenv("OPENAI_BASE_URL", "").strip()
        or PROVIDER_BASE_URLS.get(AI_PROVIDER, "https://api.openai.com/v1")
    )
    ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
    ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

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
