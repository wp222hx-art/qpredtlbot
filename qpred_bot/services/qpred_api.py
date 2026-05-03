"""
QPred 官方 API 对接 (含降级模拟数据)
- JYC 价格行情
- 热门预测市场
- 平台核心指标
- 自动 fallback 保证 Bot 可用
"""
import httpx
from typing import List, Dict
from config import config
from logger_config import logger


class QPredAPI:
    """
    注: 如 QPred 官方 API 尚未开放, 自动 fallback 到模拟数据保证 Bot 可运行
    实际对接时, 替换 fallback 逻辑为真实 API 即可
    """

    @staticmethod
    async def get_jyc_price() -> Dict:
        """获取 JYC 实时价格"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{config.QPRED_API_BASE}/v1/token/jyc")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"QPred API fallback (price): {e}")

        # Fallback 模拟数据 (基于网页实际数据)
        return {
            "price": 0.7723,
            "change_24h": 0.30,
            "volume_24h": 2_400_000,
            "market_cap": 37_700_000,
            "supply": 49_000_000,
            "holders": 8_392,
            "high_24h": 0.7896,
            "low_24h": 0.7700,
        }

    @staticmethod
    async def get_hot_markets(limit: int = 5) -> List[Dict]:
        """获取热门预测市场"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{config.QPRED_API_BASE}/v1/markets/hot",
                    params={"limit": limit}
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"QPred API fallback (markets): {e}")

        # Fallback 模拟数据
        markets = [
            {
                "id": "m001",
                "title": "比特币 5 月会达到 $95,000 吗?",
                "pool": 23681,
                "yes_odds": 2.00,
                "no_odds": 2.00,
                "apy": 17.8,
                "participants": 807,
                "deadline": "2026-05-31 23:59 UTC"
            },
            {
                "id": "m002",
                "title": "美联储将在 2026 年 6 月会议前降息吗?",
                "pool": 24650,
                "yes_odds": 2.00,
                "no_odds": 2.00,
                "apy": 15.0,
                "participants": 813,
                "deadline": "2026-06-15 23:59 UTC"
            },
            {
                "id": "m003",
                "title": "维克托·文班亚马会赢得 2025-26 NBA MVP 吗?",
                "pool": 25777,
                "yes_odds": 4.00,
                "no_odds": 1.33,
                "apy": 19.2,
                "participants": 806,
                "deadline": "2026-06-10 23:59 UTC"
            },
            {
                "id": "m004",
                "title": "特斯拉 6 月底前成为全球市值最大公司吗?",
                "pool": 22296,
                "yes_odds": 2.13,
                "no_odds": 1.89,
                "apy": 14.0,
                "participants": 779,
                "deadline": "2026-06-30 23:59 UTC"
            },
            {
                "id": "m005",
                "title": "比特币 5 月会跌至 $70,000 吗?",
                "pool": 24650,
                "yes_odds": 2.00,
                "no_odds": 2.00,
                "apy": 17.4,
                "participants": 831,
                "deadline": "2026-05-31 23:59 UTC"
            }
        ]
        return markets[:limit]

    @staticmethod
    async def get_platform_stats() -> Dict:
        """获取平台核心指标"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{config.QPRED_API_BASE}/v1/stats")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"QPred API fallback (stats): {e}")

        return {
            "tvl": 2_000_000,
            "total_users": 117_938,
            "active_markets": 2_305,
            "total_payout": 8_500_000
        }


qpred_api = QPredAPI()
