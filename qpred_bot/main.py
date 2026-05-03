"""
QPred Telegram Bot 主入口
- 调通 Telegram Bot API (https://core.telegram.org/bots)
- 接入最强推理模型作为专属 AI 客服 (自主 RAG)
- 群守卫 + 反诈 + CAPTCHA + 反刷屏
- APScheduler 定时广播平台数据 (JYC 行情 / 热门市场)

启动: python main.py
"""
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
)
from telegram.constants import ParseMode

from config import config
from database import db
from logger_config import logger
from handlers import commands as user_cmd
from handlers import admin as admin_cmd
from handlers import guardian
from handlers import broadcaster
from handlers.faq_handler import smart_reply


# ==================== 启动钩子 ====================

async def post_init(app: Application):
    """启动初始化"""
    # 1. 验证配置
    errors = config.validate()
    for e in errors:
        logger.warning(e)

    # 2. 初始化数据库
    await db.init()

    # 3. 设置 Bot 命令菜单
    await app.bot.set_my_commands([
        BotCommand("start", "🎉 开启 QPred 之旅"),
        BotCommand("predict", "🎯 热门预测市场"),
        BotCommand("price", "💰 JYC 实时价格"),
        BotCommand("ref", "🔗 我的推广链接"),
        BotCommand("rank", "🏆 推广排行榜"),
        BotCommand("faq", "❓ 常见问题"),
        BotCommand("ask", "🤖 AI 智能问答"),
        BotCommand("help", "💬 使用帮助"),
    ])

    # 4. 启动定时广播 (基于 PTB 自带 JobQueue, 无需单独 APScheduler 进程)
    if app.job_queue:
        if config.BROADCAST_PRICE_INTERVAL > 0:
            app.job_queue.run_repeating(
                _job_broadcast_price,
                interval=config.BROADCAST_PRICE_INTERVAL * 60,
                first=config.BROADCAST_PRICE_INTERVAL * 60,
                name="broadcast_price",
            )
            logger.info(
                f"⏰ Scheduled broadcast_price every {config.BROADCAST_PRICE_INTERVAL}min"
            )
        if config.BROADCAST_MARKETS_INTERVAL > 0:
            app.job_queue.run_repeating(
                _job_broadcast_markets,
                interval=config.BROADCAST_MARKETS_INTERVAL * 60,
                first=config.BROADCAST_MARKETS_INTERVAL * 60,
                name="broadcast_markets",
            )
            logger.info(
                f"⏰ Scheduled broadcast_markets every {config.BROADCAST_MARKETS_INTERVAL}min"
            )

    logger.info("═════════════════════════════════════════")
    logger.info("🚀 QPred Telegram Bot 启动成功!")
    logger.info(f"   管理员: {config.ADMIN_IDS}")
    logger.info(f"   AI 启用: {config.ENABLE_AI} | Provider: {config.AI_PROVIDER}")
    logger.info(f"   AI 模型: {config.OPENAI_MODEL}")
    logger.info(f"   RAG 启用: {config.ENABLE_RAG}")
    logger.info(f"   群管启用: {config.ENABLE_GUARDIAN}")
    logger.info("═════════════════════════════════════════")


# ==================== 定时任务 ====================

async def _job_broadcast_price(context):
    await broadcaster.broadcast_price(context.application)


async def _job_broadcast_markets(context):
    await broadcaster.broadcast_markets(context.application)


# ==================== 兜底消息路由 ====================

async def smart_router(update: Update, context):
    """
    兜底消息处理:
    1. 群组 → 先走守卫拦截 (反诈/反刷屏/外链)
    2. 不拦截 → 交给 FAQ 智能客服 (按触发条件回答)
    """
    # 群组安全检查
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        intercepted = await guardian.check_message(update, context)
        if intercepted:
            return

    # 智能客服 (私聊 / 群里 @机器人 / 关键词)
    await smart_reply(update, context)


# ==================== 按钮回调路由 ====================

class _FakeMessage:
    """把 callback_query 包装成 message, 复用命令处理器"""
    def __init__(self, query):
        self.chat = query.message.chat
        self.from_user = query.from_user
        self._reply_target = query.message
        self.date = query.message.date

    async def reply_text(self, *args, **kwargs):
        return await self._reply_target.reply_text(*args, **kwargs)

    async def send_action(self, *args, **kwargs):
        try:
            return await self._reply_target.chat.send_action(*args, **kwargs)
        except Exception:
            return None


async def handle_callback(update: Update, context):
    """统一处理 InlineKeyboard 按钮"""
    query = update.callback_query
    if not query:
        return
    data = query.data or ""

    # CAPTCHA 验证
    if data.startswith("captcha:"):
        await guardian.handle_captcha_callback(update, context)
        return

    await query.answer()

    # 包装为 fake message, 复用命令处理器
    update.message = _FakeMessage(query)

    if data == "view_markets":
        await user_cmd.cmd_predict(update, context)
    elif data == "view_price":
        await user_cmd.cmd_price(update, context)
    elif data == "view_rank":
        await user_cmd.cmd_rank(update, context)
    elif data == "my_ref":
        await user_cmd.cmd_ref(update, context)
    elif data == "view_faq":
        await user_cmd.cmd_faq(update, context)
    elif data == "open_ai":
        await query.message.reply_text(
            "🤖 *AI 问答模式已开启*\n\n"
            "直接发送您的问题即可, 例如:\n"
            "• 双币预测是什么?\n"
            "• 如何质押 JYC?\n"
            "• 推广返佣怎么结算?",
            parse_mode=ParseMode.MARKDOWN,
        )


# ==================== Main ====================

def main():
    logger.info("⚙️  Initializing QPred Bot...")

    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN 未配置, 请编辑 .env 文件")
        return

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # 用户命令
    app.add_handler(CommandHandler("start", user_cmd.cmd_start))
    app.add_handler(CommandHandler("predict", user_cmd.cmd_predict))
    app.add_handler(CommandHandler("price", user_cmd.cmd_price))
    app.add_handler(CommandHandler("ref", user_cmd.cmd_ref))
    app.add_handler(CommandHandler("rank", user_cmd.cmd_rank))
    app.add_handler(CommandHandler("faq", user_cmd.cmd_faq))
    app.add_handler(CommandHandler("ask", user_cmd.cmd_ask))
    app.add_handler(CommandHandler("help", user_cmd.cmd_help))

    # 管理员命令
    app.add_handler(CommandHandler("stats", admin_cmd.cmd_stats))
    app.add_handler(CommandHandler("broadcast", admin_cmd.cmd_broadcast))
    app.add_handler(CommandHandler("ban", admin_cmd.cmd_ban))
    app.add_handler(CommandHandler("unban", admin_cmd.cmd_unban))
    app.add_handler(CommandHandler("reload_faq", admin_cmd.cmd_reload_faq))
    app.add_handler(CommandHandler("register_group", admin_cmd.cmd_register_group))
    app.add_handler(CommandHandler("push_markets", admin_cmd.cmd_push_markets))
    app.add_handler(CommandHandler("push_price", admin_cmd.cmd_push_price))

    # 新成员入群 → CAPTCHA
    app.add_handler(ChatMemberHandler(
        guardian.on_new_member,
        ChatMemberHandler.CHAT_MEMBER,
    ))

    # 内联按钮
    app.add_handler(CallbackQueryHandler(handle_callback))

    # 兜底文本路由 (群守卫 + 智能客服)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        smart_router,
    ))

    logger.info("🚀 Starting polling...")
    app.run_polling(
        allowed_updates=["message", "callback_query", "chat_member"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
