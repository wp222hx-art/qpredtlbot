"""
SQLite 数据库管理
存储: 用户信息、积分、推广关系、警告记录、消息日志、FAQ日志
"""
import aiosqlite
import os
from typing import Optional, List, Dict
from config import config
from logger_config import logger


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    async def init(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    ref_code TEXT UNIQUE,
                    parent_ref TEXT,
                    points INTEGER DEFAULT 0,
                    total_invites INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'zh',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS message_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    message_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS faq_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    question TEXT,
                    answer TEXT,
                    matched_faq TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS broadcast_targets (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_warn_user ON warnings(user_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_msg_user_time ON message_logs(user_id, created_at)"
            )
            await db.commit()
        logger.info("✅ Database initialized")

    async def add_user(self, user_id: int, username: str, first_name: str,
                       ref_code: str, parent_ref: Optional[str] = None) -> bool:
        """新增用户, 返回是否为新用户"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
                )
                existing = await cursor.fetchone()
                if existing:
                    await db.execute(
                        "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                        (user_id,)
                    )
                    await db.commit()
                    return False

                await db.execute(
                    """INSERT INTO users
                       (user_id, username, first_name, ref_code, parent_ref)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, username, first_name, ref_code, parent_ref)
                )
                if parent_ref:
                    await db.execute(
                        """UPDATE users
                           SET points = points + 100, total_invites = total_invites + 1
                           WHERE ref_code = ?""",
                        (parent_ref,)
                    )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"add_user error: {e}")
            return False

    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_warning(self, user_id: int, chat_id: int, reason: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO warnings (user_id, chat_id, reason) VALUES (?, ?, ?)",
                (user_id, chat_id, reason)
            )
            cursor = await db.execute(
                "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            )
            count = (await cursor.fetchone())[0]
            await db.commit()
            return count

    async def log_message(self, user_id: int, chat_id: int, msg_type: str = "text"):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO message_logs (user_id, chat_id, message_type) VALUES (?, ?, ?)",
                (user_id, chat_id, msg_type)
            )
            await db.commit()

    async def count_recent_messages(self, user_id: int, seconds: int = 10) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"""SELECT COUNT(*) FROM message_logs
                    WHERE user_id = ?
                    AND created_at >= datetime('now', '-{seconds} seconds')""",
                (user_id,)
            )
            return (await cursor.fetchone())[0]

    async def log_faq(self, user_id: int, question: str, answer: str, matched: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO faq_logs (user_id, question, answer, matched_faq) VALUES (?, ?, ?, ?)",
                (user_id, question, answer, matched)
            )
            await db.commit()

    async def get_stats(self) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            stats = {}
            cursor = await db.execute("SELECT COUNT(*) as c FROM users")
            stats["total_users"] = (await cursor.fetchone())["c"]
            cursor = await db.execute(
                "SELECT COUNT(*) as c FROM users WHERE DATE(created_at) = DATE('now')"
            )
            stats["new_today"] = (await cursor.fetchone())["c"]
            cursor = await db.execute(
                """SELECT COUNT(DISTINCT user_id) as c FROM message_logs
                   WHERE DATE(created_at) = DATE('now')"""
            )
            stats["active_today"] = (await cursor.fetchone())["c"]
            cursor = await db.execute("SELECT COUNT(*) as c FROM warnings")
            stats["total_warnings"] = (await cursor.fetchone())["c"]
            cursor = await db.execute("SELECT COUNT(*) as c FROM faq_logs")
            stats["total_faq_queries"] = (await cursor.fetchone())["c"]
            return stats

    async def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT username, first_name, points, total_invites
                   FROM users
                   ORDER BY points DESC
                   LIMIT ?""",
                (limit,)
            )
            return [dict(r) for r in await cursor.fetchall()]

    async def register_broadcast_target(self, chat_id: int, title: str = ""):
        """登记一个广播目标群"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO broadcast_targets (chat_id, title, enabled)
                   VALUES (?, ?, 1)""",
                (chat_id, title)
            )
            await db.commit()

    async def list_broadcast_targets(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT chat_id FROM broadcast_targets WHERE enabled = 1"
            )
            return [r[0] for r in await cursor.fetchall()]


db = Database()
