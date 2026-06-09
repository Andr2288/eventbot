"""Ініціалізація SQLite бази даних."""

import aiosqlite
import os
from contextlib import asynccontextmanager

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "eventbot.db"))


@asynccontextmanager
async def get_db():
    """Контекстний менеджер — відкриває з'єднання, закриває після блоку."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn


async def init_db() -> None:
    """Створити таблиці якщо не існують."""
    async with get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username    TEXT    DEFAULT '',
                full_name   TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(telegram_id),
                title       TEXT    NOT NULL,
                event_date  TEXT    NOT NULL,
                event_time  TEXT    DEFAULT NULL,
                description TEXT    DEFAULT NULL,
                status      TEXT    DEFAULT 'pending',
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id        INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                user_id         INTEGER NOT NULL,
                remind_at       TEXT    NOT NULL,
                sent            INTEGER DEFAULT 0,
                reminder_type   TEXT    DEFAULT 'custom'
            );

            CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
            CREATE INDEX IF NOT EXISTS idx_reminders_event ON reminders(event_id);
            CREATE INDEX IF NOT EXISTS idx_reminders_sent ON reminders(sent, remind_at);
        """)
        await _migrate_events_status(db)
        await db.commit()


async def _migrate_events_status(db: aiosqlite.Connection) -> None:
    """Додати колонку status до існуючих БД (без перестворення таблиці)."""
    cursor = await db.execute("PRAGMA table_info(events)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "status" not in columns:
        await db.execute(
            "ALTER TABLE events ADD COLUMN status TEXT DEFAULT 'pending'"
        )
