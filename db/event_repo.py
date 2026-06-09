"""Репозиторій подій."""

from datetime import datetime, date

from db.database import get_db
from services.security_service import decrypt_event, encrypt_field


def _rows_to_events(rows) -> list[dict]:
    return [decrypt_event(dict(r)) for r in rows]


async def add_event(
    user_id: int,
    title: str,
    event_date: str,
    event_time: str | None,
    description: str | None,
) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO events (user_id, title, event_date, event_time, description, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (
                user_id,
                encrypt_field(title),
                event_date,
                event_time,
                encrypt_field(description),
                datetime.now().isoformat(),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_events_by_day(user_id: int, day: str) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM events WHERE user_id = ? AND event_date = ? ORDER BY event_time",
            (user_id, day),
        )
        rows = await cursor.fetchall()
        return _rows_to_events(rows)


async def get_events_by_week(user_id: int, start: str, end: str) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM events WHERE user_id = ? AND event_date BETWEEN ? AND ? ORDER BY event_date, event_time",
            (user_id, start, end),
        )
        rows = await cursor.fetchall()
        return _rows_to_events(rows)


async def get_all_events(user_id: int) -> list[dict]:
    today = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM events WHERE user_id = ? AND event_date >= ? ORDER BY event_date, event_time",
            (user_id, today),
        )
        rows = await cursor.fetchall()
        return _rows_to_events(rows)


async def get_event_by_id(event_id: int, user_id: int) -> dict | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM events WHERE id = ? AND user_id = ?",
            (event_id, user_id),
        )
        row = await cursor.fetchone()
        return decrypt_event(dict(row)) if row else None


async def update_event(
    event_id: int,
    user_id: int,
    title: str,
    event_date: str,
    event_time: str | None,
    description: str | None,
) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            """UPDATE events SET title=?, event_date=?, event_time=?, description=?
               WHERE id=? AND user_id=?""",
            (
                encrypt_field(title),
                event_date,
                event_time,
                encrypt_field(description),
                event_id,
                user_id,
            ),
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_event(event_id: int, user_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM events WHERE id=? AND user_id=?",
            (event_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_event_status(event_id: int, user_id: int, status: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "UPDATE events SET status = ? WHERE id = ? AND user_id = ?",
            (status, event_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_all_events(user_id: int) -> int:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM events WHERE user_id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount


async def get_upcoming_events_for_reminders() -> list[dict]:
    today = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM events WHERE event_date >= ? ORDER BY event_date, event_time",
            (today,),
        )
        rows = await cursor.fetchall()
        return _rows_to_events(rows)
