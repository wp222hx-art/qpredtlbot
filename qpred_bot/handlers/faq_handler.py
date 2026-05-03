"""
FAQ 智能路由
- 群组中: 仅在 @机器人 / 回复机器人 / 含关键词时触发, 不打扰日常聊天
- 私聊中: 任意非命令文本均走 AI 问答
- 自动注入平台实时数据 (JYC 价格 / 平台指标) 做 RAG
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import config
from database import db
from services.ai_service import ai_service
from services.qpred_api import qpred_api
from logger_config import logger


# 触发 AI 客服的关键词 (群里出现这些词才会主动回答)
TRIGGER_KEYWORDS = [
    "qpred", "JYC", "jyc", "客服", "ai", "AI",
    "怎么", "如何", "为什么", "什么是", "请问",
    "充值", "提现", "质押", "推广", "返佣",
    "钱包", "赔率", "APY", "结算",
]


async def _build_realtime_context() -> str:
    """构造平台实时数据片段, 用于 RAG 上下文"""
    try:
        price = await qpred_api.get_jyc_price()
        stats = await qpred_api.get_platform_stats()
        return (
            f"JYC 实时基准价: ${price['price']:.4f}, 24h 浮动 {price['change_24h']:+.2f}%, "
            f"流通市值 ${price['market_cap']:,}, 持币 {price['holders']:,}.\n"
            f"平台 TVL ${stats['tvl']:,}, 用户 {stats['total_users']:,}, "
            f"活跃市场 {stats['active_markets']:,}, 累计派发 ${stats['total_payout']:,}."
        )
    except Exception as e:
        logger.warning(f"build realtime context failed: {e}")
        return ""


def _should_trigger(update: Update, bot_username: str) -> bool:
    """判断群消息是否应触发 AI 应答"""
    msg = update.message
    if not msg or not msg.text:
        return False

    chat = update.effective_chat
    text = msg.text or ""

    # 私聊全部触发
    if chat.type == "private":
        return True

    # 1) @机器人
    if bot_username and f"@{bot_username}" in text:
        return True

    # 2) 回复机器人
    if msg.reply_to_message and msg.reply_to_message.from_user \
            and msg.reply_to_message.from_user.is_bot:
        return True

    # 3) 出现客服关键词
    low = text.lower()
    if any(kw.lower() in low for kw in TRIGGER_KEYWORDS):
        return True

    return False


async def smart_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """统一 AI 问答入口 (供 main.py 调用)"""
    msg = update.message
    if not msg or not msg.text:
        return

    bot = await context.bot.get_me()
    if not _should_trigger(update, bot.username or ""):
        return

    # 群内: 去掉 @bot 前缀
    question = msg.text
    if bot.username:
        question = question.replace(f"@{bot.username}", "").strip()
    if not question:
        return

    # 跳过命令
    if question.startswith("/"):
        return

    try:
        await msg.chat.send_action("typing")
    except Exception:
        pass

    extra = await _build_realtime_context() if config.ENABLE_RAG else ""
    answer = await ai_service.answer(question, extra_context=extra)
    await db.log_faq(update.effective_user.id, question, answer)

    # 用普通文本回复, 避免 Markdown 转义问题
    try:
        await msg.reply_text(answer, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"smart_reply send failed: {e}")
