"""
管理员专用命令 (仅 ADMIN_IDS 可用)
- /stats /broadcast /ban /unban /reload_faq /push_markets /push_price /register_group
"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import config
from database import db
from services.qpred_api import qpred_api
from logger_config import logger


def admin_only(func):
    """管理员权限校验装饰器"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("⛔ 此命令仅限管理员使用")
            logger.warning(f"Unauthorized admin access: {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats - 平台数据统计"""
    stats = await db.get_stats()

    text = (
        "📊 <b>QPred Bot 运营数据</b>\n\n"
        f"👥 <b>用户总数</b>: {stats['total_users']:,}\n"
        f"✨ <b>今日新增</b>: {stats['new_today']}\n"
        f"🔥 <b>今日活跃</b>: {stats['active_today']}\n"
        f"⚠️ <b>累计警告</b>: {stats['total_warnings']}\n"
        f"🤖 <b>AI 问答总量</b>: {stats.get('total_faq_queries', 0)}\n\n"
        "🕐 统计时间: 实时"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@admin_only
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast <消息> - 群发广播 (向所有已登记群组)"""
    if not context.args:
        await update.message.reply_text(
            "用法: <code>/broadcast 消息内容</code>", parse_mode=ParseMode.HTML
        )
        return

    message = " ".join(context.args)
    targets = await db.list_broadcast_targets()
    if config.GROUP_CHAT_ID and config.GROUP_CHAT_ID not in targets:
        targets.append(config.GROUP_CHAT_ID)

    if not targets:
        await update.message.reply_text(
            "⚠️ 没有可广播的群组, 请先在目标群发送 /register_group"
        )
        return

    success, fail = 0, 0
    for chat_id in targets:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📢 <b>官方公告</b>\n\n{message}",
                parse_mode=ParseMode.HTML,
            )
            success += 1
        except Exception as e:
            fail += 1
            logger.warning(f"Broadcast to {chat_id} failed: {e}")

    await update.message.reply_text(
        f"✅ 广播完成 | 成功 {success} | 失败 {fail}"
    )
    logger.info(f"Broadcast by admin {update.effective_user.id}: {message[:80]}")


@admin_only
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ban - 回复目标用户执行封禁"""
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ 请回复目标用户的消息使用 /ban")
        return

    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
        )
        await update.message.reply_text(
            f"🚫 已封禁用户 {target.mention_html()}",
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"User {target.id} banned by admin {update.effective_user.id}")
    except Exception as e:
        await update.message.reply_text(f"❌ 封禁失败: {e}")


@admin_only
async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unban <user_id> - 解封"""
    if not context.args:
        await update.message.reply_text(
            "用法: <code>/unban &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML
        )
        return

    try:
        target_id = int(context.args[0])
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_id,
        )
        await update.message.reply_text(f"✅ 已解封用户 {target_id}")
        logger.info(f"User {target_id} unbanned by admin {update.effective_user.id}")
    except Exception as e:
        await update.message.reply_text(f"❌ 解封失败: {e}")


@admin_only
async def cmd_reload_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reload_faq - 热重载 FAQ 知识库"""
    from services.ai_service import ai_service
    ai_service._load_faq()
    await update.message.reply_text(
        f"✅ FAQ 已重载, 当前 {len(ai_service.faq_data)} 条"
    )


@admin_only
async def cmd_register_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/register_group - 在某群发起后, 该群即被纳入广播目标"""
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("⚠️ 仅可在群组中执行")
        return
    await db.register_broadcast_target(chat.id, chat.title or "")
    await update.message.reply_text(
        f"✅ 已登记本群为广播目标\nchat_id = <code>{chat.id}</code>",
        parse_mode=ParseMode.HTML,
    )


@admin_only
async def cmd_push_markets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/push_markets - 立即向所有已登记群推送热门市场"""
    from handlers.broadcaster import broadcast_markets
    count = await broadcast_markets(context.application)
    await update.message.reply_text(f"✅ 已推送热门市场到 {count} 个群")


@admin_only
async def cmd_push_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/push_price - 立即向所有已登记群推送 JYC 行情"""
    from handlers.broadcaster import broadcast_price
    count = await broadcast_price(context.application)
    await update.message.reply_text(f"✅ 已推送 JYC 行情到 {count} 个群")
