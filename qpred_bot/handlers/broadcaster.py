"""
平台数据定时广播器
- 周期性向所有已登记群组推送 JYC 行情 / 热门预测市场
- 由 APScheduler 驱动 (在 main.py 中调度)
"""
from telegram.ext import Application
from telegram.constants import ParseMode
from config import config
from database import db
from services.qpred_api import qpred_api
from logger_config import logger


async def _collect_targets() -> list:
    targets = await db.list_broadcast_targets()
    if config.GROUP_CHAT_ID and config.GROUP_CHAT_ID not in targets:
        targets.append(config.GROUP_CHAT_ID)
    return targets


async def broadcast_price(application: Application) -> int:
    """推送 JYC 实时行情"""
    targets = await _collect_targets()
    if not targets:
        return 0

    p = await qpred_api.get_jyc_price()
    emoji = "🟢" if p["change_24h"] >= 0 else "🔴"
    text = (
        "💎 <b>JYC / USDT · 实时行情速递</b>\n\n"
        f"💵 基准价: <b>${p['price']:.4f}</b>\n"
        f"{emoji} 24h 浮动: {p['change_24h']:+.2f}%\n"
        f"📊 24h 成交: ${p['volume_24h']:,.0f}\n"
        f"💰 流通市值: ${p['market_cap']:,.0f}\n"
        f"👥 持币地址: {p['holders']:,}\n\n"
        f"🔗 <a href=\"{config.QPRED_WEBSITE}/exchange\">立即购买 JYC</a>\n"
        f"💎 <a href=\"{config.QPRED_WEBSITE}/stake\">质押生息</a>"
    )

    success = 0
    for chat_id in targets:
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            success += 1
        except Exception as e:
            logger.warning(f"broadcast_price → {chat_id} failed: {e}")
    logger.info(f"📢 broadcast_price done | success={success}/{len(targets)}")
    return success


async def broadcast_markets(application: Application) -> int:
    """推送 TOP 5 热门预测市场"""
    targets = await _collect_targets()
    if not targets:
        return 0

    markets = await qpred_api.get_hot_markets(limit=5)
    text = "🔥 <b>QPred · 热门预测 TOP 5</b>\n\n"
    for i, m in enumerate(markets, 1):
        text += (
            f"<b>{i}. {m['title']}</b>\n"
            f"💰 奖池 ${m['pool']:,} | 📊 APY {m['apy']}%\n"
            f"✅ YES {m['yes_odds']}x | ❌ NO {m['no_odds']}x | 👥 {m['participants']} 人\n"
            f"🔗 <a href=\"{config.QPRED_WEBSITE}/predict/{m['id']}\">立即参与</a>\n\n"
        )
    text += f"🌐 <a href=\"{config.QPRED_WEBSITE}/predict\">查看全部市场</a>"

    success = 0
    for chat_id in targets:
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            success += 1
        except Exception as e:
            logger.warning(f"broadcast_markets → {chat_id} failed: {e}")
    logger.info(f"📢 broadcast_markets done | success={success}/{len(targets)}")
    return success
