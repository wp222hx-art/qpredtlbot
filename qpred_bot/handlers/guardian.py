"""
群组智能守卫
- CAPTCHA 验证 (新成员入群人机校验)
- 反刷屏 (Anti-Flood)
- 反诈骗关键词 (Spam Filter)
- 外链白名单 (Safe Domain)
- 三次警告 → 自动禁言 24h
"""
import re
import time
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import config
from database import db
from logger_config import logger


# 内存态 CAPTCHA 验证表: {user_id: expire_ts}
pending_captcha = {}


async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """新成员入群 → CAPTCHA 验证"""
    if not config.ENABLE_CAPTCHA:
        return

    chat_member = update.chat_member
    if not chat_member:
        return

    old_status = chat_member.old_chat_member.status
    new_status = chat_member.new_chat_member.status
    if not (old_status in ("left", "kicked") and new_status == "member"):
        return

    user = chat_member.new_chat_member.user
    if user.is_bot:
        return

    chat_id = chat_member.chat.id

    # 临时禁言
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
        )
    except Exception as e:
        logger.error(f"Restrict member failed: {e}")
        return

    keyboard = [[InlineKeyboardButton(
        "✅ 我是真人, 点此验证",
        callback_data=f"captcha:{user.id}"
    )]]

    try:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"👋 欢迎 {user.mention_html()} 加入 QPred 社区!\n\n"
                f"请在 {config.CAPTCHA_TIMEOUT} 秒内点击下方按钮完成验证, "
                f"否则将被移出群组。\n\n"
                f"🚫 本群严禁: 广告、诈骗、人身攻击、外链"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )

        pending_captcha[user.id] = time.time() + config.CAPTCHA_TIMEOUT

        if context.job_queue:
            context.job_queue.run_once(
                _captcha_timeout,
                config.CAPTCHA_TIMEOUT,
                data={"chat_id": chat_id, "user_id": user.id, "msg_id": msg.message_id},
                name=f"captcha_{user.id}",
            )
        logger.info(f"CAPTCHA sent to user {user.id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Send CAPTCHA failed: {e}")


async def handle_captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 CAPTCHA 按钮回调"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data or not data.startswith("captcha:"):
        return

    target_id = int(data.split(":", 1)[1])
    clicker_id = query.from_user.id

    if clicker_id != target_id:
        await query.answer("⚠️ 请勿代他人点击", show_alert=True)
        return

    try:
        await context.bot.restrict_chat_member(
            chat_id=query.message.chat.id,
            user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        pending_captcha.pop(target_id, None)

        if context.job_queue:
            for job in context.job_queue.get_jobs_by_name(f"captcha_{target_id}"):
                job.schedule_removal()

        await query.edit_message_text(
            f"✅ {query.from_user.mention_html()} 验证通过, 欢迎!\n"
            f"🎁 私聊 Bot 发送 /start 领取 100 JYC 体验金",
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"User {target_id} passed CAPTCHA")
    except Exception as e:
        logger.error(f"CAPTCHA pass failed: {e}")


async def _captcha_timeout(context: ContextTypes.DEFAULT_TYPE):
    """CAPTCHA 超时 → 踢出群组"""
    data = context.job.data
    user_id = data["user_id"]

    if user_id not in pending_captcha:
        return

    try:
        await context.bot.ban_chat_member(
            chat_id=data["chat_id"],
            user_id=user_id,
            until_date=None,
        )
        await context.bot.unban_chat_member(
            chat_id=data["chat_id"],
            user_id=user_id,
        )
        try:
            await context.bot.delete_message(
                chat_id=data["chat_id"],
                message_id=data["msg_id"],
            )
        except Exception:
            pass
        pending_captcha.pop(user_id, None)
        logger.info(f"User {user_id} kicked (CAPTCHA timeout)")
    except Exception as e:
        logger.error(f"CAPTCHA timeout handle failed: {e}")


async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    消息安全检查
    返回 True 表示已被拦截, False 表示放行
    """
    if not config.ENABLE_GUARDIAN:
        return False

    msg = update.message
    if not msg or not msg.text:
        return False

    user = update.effective_user
    chat = update.effective_chat

    # 管理员豁免
    if user.id in config.ADMIN_IDS:
        return False

    # 私聊豁免
    if chat.type == "private":
        return False

    text = msg.text.lower()
    await db.log_message(user.id, chat.id)

    # 1. 反刷屏
    recent = await db.count_recent_messages(user.id, seconds=config.ANTI_FLOOD_WINDOW)
    if recent > config.ANTI_FLOOD_MAX:
        await _mute(update, context, minutes=30, reason="刷屏")
        return True

    # 2. 反诈骗关键词
    for pattern in config.SPAM_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            try:
                await msg.delete()
            except Exception:
                pass
            warnings = await db.add_warning(user.id, chat.id, f"诈骗关键词: {pattern}")
            await _warn(update, context, reason="疑似诈骗内容", count=warnings)
            return True

    # 3. 外链白名单
    urls = re.findall(r"https?://([^\s/]+)", text)
    for url in urls:
        if not any(safe in url.lower() for safe in config.SAFE_DOMAINS):
            try:
                await msg.delete()
            except Exception:
                pass
            warnings = await db.add_warning(user.id, chat.id, f"非白名单链接: {url}")
            await _warn(update, context, reason=f"禁止非白名单链接 ({url})", count=warnings)
            return True

    return False


async def _mute(update: Update, context: ContextTypes.DEFAULT_TYPE, minutes: int, reason: str):
    """禁言用户"""
    user = update.effective_user
    chat = update.effective_chat
    until = update.message.date + timedelta(minutes=minutes)

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        try:
            await update.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"🚫 用户 {user.mention_html()} 因【{reason}】被禁言 {minutes} 分钟",
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"User {user.id} muted {minutes}min - {reason}")
    except Exception as e:
        logger.error(f"Mute failed: {e}")


async def _warn(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str, count: int):
    """警告累计, 3次自动禁言24h"""
    user = update.effective_user
    chat = update.effective_chat

    if count >= 3:
        await _mute(update, context, minutes=24 * 60, reason=f"累计3次警告 ({reason})")
    else:
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"⚠️ 警告 {user.mention_html()}\n"
                    f"原因: {reason}\n"
                    f"当前警告次数: {count}/3 (累计 3 次禁言 24 小时)"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"Warn send failed: {e}")
