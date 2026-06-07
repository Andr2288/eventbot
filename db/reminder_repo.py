"""Репозиторій нагадувань."""

from datetime import datetime
from db.database import get_db


async def add_reminder(event_id: int, user_id: int, remind_at: datetime, reminder_type: str = "custom") -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO reminders (event_id, user_id, remind_at, sent, reminder_type) VALUES (?, ?, ?, 0, ?)",
            (event_id, user_id, remind_at.isoformat(), reminder_type),
        )
        await db.commit()
        return cursor.lastrowid


async def get_reminders_for_event(event_id: int) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE event_id = ? ORDER BY remind_at",
            (event_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_due_reminders(now: datetime) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT r.*, e.title, e.event_date, e.event_time, e.description
               FROM reminders r
               JOIN events e ON e.id = r.event_id
               WHERE r.sent = 0 AND r.remind_at <= ?
               ORDER BY r.remind_at""",
            (now.isoformat(),),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_sent(reminder_id: int) -> None:
    async with get_db() as db:
        await db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()


async def delete_reminders_for_event(event_id: int) -> None:
    async with get_db() as db:
        await db.execute("DELETE FROM reminders WHERE event_id = ?", (event_id,))
        await db.commit()
