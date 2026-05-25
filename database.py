import os
from datetime import datetime
from typing import Optional, Any

import aiosqlite


DB_PATH = os.getenv("DATABASE_PATH", "bot_data.sqlite3")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            bot_language TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            is_blocked INTEGER NOT NULL DEFAULT 0,
            messages_count INTEGER NOT NULL DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            instrument TEXT,
            deposit REAL,
            open_price REAL,
            sl_price REAL,
            risk_type TEXT,
            risk_value REAL,
            lot REAL,
            risk_text TEXT,
            created_at TEXT NOT NULL
        )
        """)

        await db.commit()


async def upsert_user(tg_user: Any) -> Optional[str]:
    """
    Создаёт или обновляет пользователя.
    Возвращает bot_language, если пользователь раньше выбирал язык в боте.
    """
    if not tg_user:
        return None

    created_at = now_str()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        await db.execute("""
        INSERT INTO users (
            user_id,
            username,
            first_name,
            last_name,
            language_code,
            first_seen,
            last_seen,
            is_blocked,
            messages_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            language_code = excluded.language_code,
            last_seen = excluded.last_seen,
            is_blocked = 0,
            messages_count = messages_count + 1
        """, (
            tg_user.id,
            tg_user.username,
            tg_user.first_name,
            tg_user.last_name,
            tg_user.language_code,
            created_at,
            created_at
        ))

        await db.commit()

        cursor = await db.execute(
            "SELECT bot_language FROM users WHERE user_id = ?",
            (tg_user.id,)
        )
        row = await cursor.fetchone()

        if row and row["bot_language"]:
            return row["bot_language"]

        return None


async def update_user_language(user_id: int, lang: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE users
        SET bot_language = ?, last_seen = ?
        WHERE user_id = ?
        """, (lang, now_str(), user_id))
        await db.commit()


async def log_activity(user_id: int, action: str, details: Optional[str] = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO activity_logs (user_id, action, details, created_at)
        VALUES (?, ?, ?, ?)
        """, (user_id, action, details, now_str()))
        await db.commit()


async def save_calculation(
    user_id: int,
    instrument: str,
    deposit: float,
    open_price: float,
    sl_price: float,
    risk_type: str,
    risk_value: float,
    lot: float,
    risk_text: str
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO calculations (
            user_id,
            instrument,
            deposit,
            open_price,
            sl_price,
            risk_type,
            risk_value,
            lot,
            risk_text,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            instrument,
            deposit,
            open_price,
            sl_price,
            risk_type,
            risk_value,
            lot,
            risk_text,
            now_str()
        ))
        await db.commit()


async def get_user_stats() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT
            COUNT(*) AS total_users,
            SUM(CASE WHEN is_blocked = 1 THEN 1 ELSE 0 END) AS blocked_users,
            SUM(CASE WHEN last_seen LIKE ? THEN 1 ELSE 0 END) AS active_today,
            SUM(messages_count) AS total_messages
        FROM users
        """, (f"{today}%",))
        totals = dict(await cursor.fetchone())

        cursor = await db.execute("""
        SELECT
            COALESCE(bot_language, language_code, 'unknown') AS lang,
            COUNT(*) AS count
        FROM users
        GROUP BY lang
        ORDER BY count DESC
        """)
        languages = [dict(row) for row in await cursor.fetchall()]

        cursor = await db.execute("""
        SELECT COUNT(*) AS total_calculations
        FROM calculations
        """)
        calculations = dict(await cursor.fetchone())

        return {
            "totals": totals,
            "languages": languages,
            "calculations": calculations
        }


async def get_users(limit: int = 30) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT
            user_id,
            username,
            first_name,
            last_name,
            COALESCE(bot_language, language_code, 'unknown') AS lang,
            first_seen,
            last_seen,
            is_blocked,
            messages_count
        FROM users
        ORDER BY last_seen DESC
        LIMIT ?
        """, (limit,))

        return [dict(row) for row in await cursor.fetchall()]


async def get_user_logs(user_id: int, limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT action, details, created_at
        FROM activity_logs
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """, (user_id, limit))

        return [dict(row) for row in await cursor.fetchall()]


async def get_all_active_users() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
        SELECT user_id
        FROM users
        WHERE is_blocked = 0
        ORDER BY last_seen DESC
        """)

        rows = await cursor.fetchall()
        return [int(row[0]) for row in rows]


async def mark_user_blocked(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE users
        SET is_blocked = 1
        WHERE user_id = ?
        """, (user_id,))
        await db.commit()
