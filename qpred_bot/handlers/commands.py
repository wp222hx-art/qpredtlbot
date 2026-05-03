"""
用户基础命令处理
- /start /predict /price /ref /rank /faq /ask /help /stake
- 内联键盘按钮交互
- MarkdownV2 安全转义
"""
import secrets
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import config
from database import db
from services.qpred_api import qpred_api
from services.ai_service import ai_service
from logger_config import logger


def generate_ref_code(length: int = 8) -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def _escape(text: str) -> str:
    """MarkdownV2 转义 (Telegram Bot API 要求)"""
    if not text:
        return ""
    chars = r"_*[]()~`>#+-=|{}.!\\"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start - 新用户注册 + 欢迎"""
    user = update.effective_user
    parent_ref = context.args[0] if context.args else None

    ref_code = generate_ref_code()
    is_new = await db.add_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "Anonymous",
        ref_code=ref_code,
        parent_ref=parent_ref,
    )

    existing = await db.get_user(user.id)
    user_ref = existing["ref_code"] if existing else ref_code

    name_safe = _escape(user.first_name or "Anonymous")
    site_safe = _escape(config.QPRED_WEBSITE)

    text = (
        f"🎉 *欢迎 {name_safe} 加入 QPred\\!*\n\n"
        f"🌟 *全球首个双币预测平台*\n"
        f"💎 TVL $2M · 用户 11\\.7万 · 活跃市场 2,305\\+\n\n"
        f"🎁 *新人专属福利*\n"
        f"✅ 100 JYC 体验金 \\(零风险免费玩\\)\n"
        f"✅ 专属推广链接已生成\n\n"
        f"🔗 *您的推广链接*\n"
        f"`{site_safe}/ref/{user_ref}`\n\n"
        f"邀请好友, 永久 5% 返佣 💰\n\n"
        f"选择下一步操作 👇"
    )

    keyboard = [
        [
            InlineKeyboardButton("🎯 预测市场", callback_data="view_markets"),
            InlineKeyboardButton("💰 JYC 价格", callback_data="view_price"),
        ],
        [
            InlineKeyboardButton("🔗 我的推广", callback_data="my_ref"),
            InlineKeyboardButton("🏆 排行榜", callback_data="view_rank"),
        ],
        [
            InlineKeyboardButton("❓ FAQ", callback_data="view_faq"),
            InlineKeyboardButton("🤖 AI 问答", callback_data="open_ai"),
        ],
        [InlineKeyboardButton("🌐 访问官网", url=config.QPRED_WEBSITE)],
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    logger.info(f"User {user.id} ({user.first_name}) started, new={is_new}")


async def cmd_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/predict - 热门预测市场"""
    markets = await qpred_api.get_hot_markets(limit=5)

    text = "🔥 *当前最热预测市场 TOP 5*\n\n"
    buttons = []
    for i, m in enumerate(markets, 1):
        text += (
            f"*{i}\\. {_escape(m['title'])}*\n"
            f"💰 奖池 ${m['pool']:,} \\| 📊 APY {m['apy']}%\n"
            f"✅ YES {m['yes_odds']}x \\| ❌ NO {m['no_odds']}x\n"
            f"👥 {m['participants']} 人参与\n\n"
        )
        buttons.append([InlineKeyboardButton(
            f"参与 #{i}",
            url=f"{config.QPRED_WEBSITE}/predict/{m['id']}"
        )])

    buttons.append([InlineKeyboardButton(
        "🌐 查看全部市场", url=f"{config.QPRED_WEBSITE}/predict"
    )])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/price - JYC 实时价格"""
    p = await qpred_api.get_jyc_price()
    emoji = "🟢" if p["change_24h"] >= 0 else "🔴"

    raw_text = (
        f"💎 *JYC / USDT 实时行情*\n\n"
        f"💵 基准价: *${p['price']:.4f}*\n"
        f"{emoji} 24h 浮动: {p['change_24h']:+.2f}%\n"
        f"📊 24h 成交: ${p['volume_24h']:,.0f}\n"
        f"💰 流通市值: ${p['market_cap']:,.0f}\n"
        f"🪙 流通量: {p['supply']:,.0f}\n"
        f"👥 持币地址: {p['holders']:,}\n\n"
        f"📈 24h 最高: ${p['high_24h']:.4f}\n"
        f"📉 24h 最低: ${p['low_24h']:.4f}\n\n"
        f"🔗 链上定价 · 透明可查\n"
        f"⚠️ 日浮动限制 ±3.00%"
    )

    # 用 HTML 输出避免复杂转义
    html_text = (
        f"💎 <b>JYC / USDT 实时行情</b>\n\n"
        f"💵 基准价: <b>${p['price']:.4f}</b>\n"
        f"{emoji} 24h 浮动: {p['change_24h']:+.2f}%\n"
        f"📊 24h 成交: ${p['volume_24h']:,.0f}\n"
        f"💰 流通市值: ${p['market_cap']:,.0f}\n"
        f"🪙 流通量: {p['supply']:,.0f}\n"
        f"👥 持币地址: {p['holders']:,}\n\n"
        f"📈 24h 最高: ${p['high_24h']:.4f}\n"
        f"📉 24h 最低: ${p['low_24h']:.4f}\n\n"
        f"🔗 链上定价 · 透明可查\n"
        f"⚠️ 日浮动限制 ±3.00%"
    )

    keyboard = [[
        InlineKeyboardButton("💰 购买 JYC", url=f"{config.QPRED_WEBSITE}/exchange"),
        InlineKeyboardButton("💎 质押生息", url=f"{config.QPRED_WEBSITE}/stake"),
    ]]

    await update.message.reply_text(
        html_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


async def cmd_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ref - 我的推广链接"""
    user_id = update.effective_user.id
    user_data = await db.get_user(user_id)

    if not user_data:
        await update.message.reply_text("⚠️ 请先发送 /start 完成注册")
        return

    site_safe = _escape(config.QPRED_WEBSITE)
    text = (
        f"🔗 *您的专属推广中心*\n\n"
        f"📎 *推广链接*\n"
        f"`{site_safe}/ref/{user_data['ref_code']}`\n\n"
        f"📊 *数据看板*\n"
        f"👥 邀请人数: *{user_data['total_invites']}*\n"
        f"⭐ 积分余额: *{user_data['points']}*\n\n"
        f"💎 *返佣规则*\n"
        f"• 好友注册 \\+100 积分\n"
        f"• 好友首充 \\+500 积分\n"
        f"• 好友下单 永久 5% 返佣\n\n"
        f"立即分享, 躺赚收益 🚀"
    )

    keyboard = [
        [InlineKeyboardButton(
            "📤 一键分享",
            switch_inline_query=(
                f"加入 QPred 全球首个双币预测平台! 新人送 100 JYC! "
                f"{config.QPRED_WEBSITE}/ref/{user_data['ref_code']}"
            ),
        )],
        [
            InlineKeyboardButton("🏆 排行榜", callback_data="view_rank"),
            InlineKeyboardButton("📊 详细数据", url=f"{config.QPRED_WEBSITE}/dashboard"),
        ],
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/rank - 排行榜"""
    leaderboard = await db.get_leaderboard(limit=10)

    if not leaderboard:
        await update.message.reply_text("🏆 排行榜暂无数据, 快来成为第一名!")
        return

    text = "🏆 *QPred 推广大神榜 TOP 10*\n\n"
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

    for i, u in enumerate(leaderboard):
        name = u["first_name"] or u["username"] or "Anonymous"
        text += (
            f"{medals[i]} *{_escape(name)}*\n"
            f"   积分 {u['points']} \\| 邀请 {u['total_invites']} 人\n\n"
        )

    text += "💪 本周继续冲刺\\!"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ask - AI 智能问答 (带平台实时数据 RAG)"""
    question = " ".join(context.args) if context.args else ""

    if not question:
        await update.message.reply_text(
            "💡 用法: <code>/ask 你的问题</code>\n"
            "例如: <code>/ask 双币预测是什么?</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass

    # 注入实时平台数据 (RAG)
    extra = ""
    try:
        price = await qpred_api.get_jyc_price()
        stats = await qpred_api.get_platform_stats()
        extra = (
            f"JYC 实时基准价: ${price['price']:.4f}, 24h 浮动 {price['change_24h']:+.2f}%, "
            f"流通市值 ${price['market_cap']:,}, 持币 {price['holders']:,}.\n"
            f"平台 TVL ${stats['tvl']:,}, 用户 {stats['total_users']:,}, "
            f"活跃市场 {stats['active_markets']:,}, 累计派发 ${stats['total_payout']:,}."
        )
    except Exception as e:
        logger.warning(f"Inject realtime data failed: {e}")

    answer = await ai_service.answer(question, extra_context=extra)
    await db.log_faq(update.effective_user.id, question, answer)

    # 用普通文本发送, 避免 Markdown 转义出错
    await update.message.reply_text(answer)


async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/faq - 常见问题列表"""
    text = "❓ *QPred 常见问题*\n\n"
    for i, faq in enumerate(ai_service.faq_data, 1):
        text += f"{i}\\. {_escape(faq['question'])}\n"
    text += "\n💬 直接发消息或用 `/ask <问题>` 提问 AI"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help - 帮助菜单"""
    text = (
        "🆘 <b>QPred Bot 使用指南</b>\n\n"
        "📋 <b>用户命令</b>\n"
        "/start - 开启之旅 / 获取推广链接\n"
        "/predict - 热门预测市场\n"
        "/price - JYC 实时价格\n"
        "/ref - 我的推广中心\n"
        "/rank - 推广排行榜\n"
        "/faq - 常见问题\n"
        "/ask - AI 智能问答 (示例: /ask 怎么质押)\n\n"
        f"🌐 <b>官网</b>: {config.QPRED_WEBSITE}\n"
        "📢 <b>官方频道</b>: @qpred_official\n\n"
        "💬 <b>联系人工</b>\n"
        "• 邮箱: support@qpred.io\n"
        f"• 工单: {config.QPRED_WEBSITE}/support"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
