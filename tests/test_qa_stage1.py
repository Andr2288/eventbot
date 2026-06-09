"""QA Етап 1. Ручний чеклист: qa/QA_STAGE1.md"""

from cryptography.fernet import Fernet

import db.event_repo as event_repo
import db.reminder_repo as reminder_repo
import db.user_repo as user_repo
from handlers.keyboards import settings_menu
from services import account_service, security_service


class TestQaStage1Encryption:
    def test_encrypt_decrypt_roundtrip(self, monkeypatch):
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", key)
        security_service.reset_encryption_cache()

        encrypted = security_service.encrypt_field("Секретна задача")
        assert encrypted != "Секретна задача"
        assert security_service.decrypt_field(encrypted) == "Секретна задача"

    def test_decrypt_legacy_plain_text(self, monkeypatch):
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", key)
        security_service.reset_encryption_cache()

        assert security_service.decrypt_field("звичайний текст") == "звичайний текст"

    async def test_event_stored_encrypted_when_key_set(self, test_db, monkeypatch):
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", key)
        security_service.reset_encryption_cache()

        user_id = 201
        await user_repo.get_or_create_user(user_id, "u", "User")
        event_id = await event_repo.add_event(user_id, "Таємниця", "2099-06-01", None, "опис")

        import aiosqlite
        import db.database as database

        async with aiosqlite.connect(database.DB_PATH) as conn:
            cursor = await conn.execute(
                "SELECT title FROM events WHERE id = ?", (event_id,)
            )
            raw_title = (await cursor.fetchone())[0]

        assert raw_title != "Таємниця"
        event = await event_repo.get_event_by_id(event_id, user_id)
        assert event["title"] == "Таємниця"


class TestQaStage1BulkActions:
    async def test_delete_all_events_only_own(self, test_db):
        await user_repo.get_or_create_user(301, "a", "A")
        await user_repo.get_or_create_user(302, "b", "B")
        id_a = await event_repo.add_event(301, "A1", "2099-01-01", None, None)
        id_b = await event_repo.add_event(302, "B1", "2099-01-01", None, None)

        count = await account_service.delete_all_events(301)

        assert count == 1
        assert await event_repo.get_event_by_id(id_a, 301) is None
        assert await event_repo.get_event_by_id(id_b, 302) is not None

    async def test_clear_all_reminders(self, test_db):
        user_id = 401
        await user_repo.get_or_create_user(user_id, "u", "User")
        event_id = await event_repo.add_event(user_id, "E", "2099-01-01", "10:00", None)
        from datetime import datetime, timedelta

        await reminder_repo.add_reminder(
            event_id, user_id, datetime.now() + timedelta(hours=1), "1hour"
        )

        count = await account_service.clear_all_reminders(user_id)

        assert count == 1
        assert await reminder_repo.get_reminders_for_event(event_id) == []
        assert await event_repo.get_event_by_id(event_id, user_id) is not None

    async def test_delete_account_removes_user_data(self, test_db):
        user_id = 501
        await user_repo.get_or_create_user(user_id, "u", "User")
        await event_repo.add_event(user_id, "E", "2099-01-01", None, None)

        ok = await account_service.delete_account(user_id)

        assert ok is True
        assert await user_repo.user_exists(user_id) is False


class TestQaStage1Auth:
    async def test_unregistered_user_blocked_after_account_delete(self, test_db):
        from middleware.auth import registration_block_reason

        user_id = 99999
        await user_repo.get_or_create_user(user_id, "u", "User")
        await account_service.delete_account(user_id)

        assert await registration_block_reason(user_id, "/today") is not None
        assert await registration_block_reason(user_id, "/start") is None


class TestQaStage1Ui:
    def test_settings_has_danger_buttons(self):
        callbacks = [
            btn.callback_data
            for row in settings_menu().inline_keyboard
            for btn in row
        ]
        assert "settings_del_events" in callbacks
        assert "settings_clear_reminders" in callbacks
        assert "settings_del_account" in callbacks

    def test_settings_router_has_confirm_handlers(self):
        from handlers import settings

        assert len(settings.router.callback_query.handlers) >= 7
