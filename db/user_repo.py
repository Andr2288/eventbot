"""Репозиторій користувачів."""

from datetime import datetime
from db.database import get_db


async def get_or_create_user(telegram_id: int, username: str, full_name: str) -> None:
    async with get_db() as db:
        row = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        exists = await row.fetchone()
        if not exists:
            await db.execute(
                "INSERT INTO users (telegram_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
                (telegram_id, username or "", full_name, datetime.now().isoformat()),
            )
            await db.commit()


async def user_exists(telegram_id: int) -> bool:
    async with get_db() as db:
        row = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return await row.fetchone() is not None


async def get_all_users() -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT telegram_id, username, full_name, created_at FROM users ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_users_count() -> int:
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def delete_user(telegram_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        await db.commit()
        return cursor.rowcount > 0
