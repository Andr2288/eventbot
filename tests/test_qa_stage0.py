"""
QA-тести — Етап 0: підготовка (міграція БД, меню налаштувань).

Ручний чеклист для тестувальника: qa/QA_STAGE0.md
"""

import aiosqlite

import db.database as database
import db.event_repo as event_repo
import db.user_repo as user_repo
from handlers.keyboards import main_menu, settings_menu


class TestQaStage0Database:
    """Міграція та поле status у таблиці events."""

    async def test_new_db_has_status_column(self, test_db):
        async with aiosqlite.connect(str(test_db)) as conn:
            cursor = await conn.execute("PRAGMA table_info(events)")
            columns = {row[1]: row[2] for row in await cursor.fetchall()}

        assert "status" in columns

    async def test_legacy_db_migration_adds_status(self, tmp_path, monkeypatch):
        """Імітація старої БД без колонки status."""
        db_file = tmp_path / "legacy.db"
        async with aiosqlite.connect(str(db_file)) as conn:
            await conn.executescript("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT, full_name TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                    title TEXT NOT NULL, event_date TEXT NOT NULL,
                    event_time TEXT, description TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE reminders (
                    id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL, remind_at TEXT NOT NULL,
                    sent INTEGER DEFAULT 0, reminder_type TEXT DEFAULT 'custom'
                );
            """)
            await conn.commit()

        monkeypatch.setattr(database, "DB_PATH", str(db_file))
        await database.init_db()

        async with aiosqlite.connect(str(db_file)) as conn:
            cursor = await conn.execute("PRAGMA table_info(events)")
            columns = {row[1] for row in await cursor.fetchall()}

        assert "status" in columns

    async def test_new_event_has_pending_status(self, test_db):
        user_id = 101
        await user_repo.get_or_create_user(user_id, "qa", "QA User")
        event_id = await event_repo.add_event(
            user_id, "Тест", "2099-01-01", "10:00", "опис"
        )
        event = await event_repo.get_event_by_id(event_id, user_id)

        assert event["status"] == "pending"


class TestQaStage0Ui:
    """Клавіатури та callback-дані для меню налаштувань."""

    def test_main_menu_has_settings_button(self):
        markup = main_menu()
        callbacks = [
            btn.callback_data
            for row in markup.inline_keyboard
            for btn in row
        ]

        assert "settings_menu" in callbacks
        assert "event_create_voice" in callbacks

    def test_settings_menu_has_back_button(self):
        markup = settings_menu()
        callbacks = [
            btn.callback_data
            for row in markup.inline_keyboard
            for btn in row
        ]

        assert "menu_main" in callbacks

    def test_settings_router_registered(self):
        from handlers import settings

        assert settings.router is not None
        assert len(settings.router.callback_query.handlers) >= 1
