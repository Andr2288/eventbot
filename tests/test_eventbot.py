"""Юніт-тести EventBot — мінімальний функціонал."""

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

import db.event_repo as event_repo
import db.reminder_repo as reminder_repo
import db.user_repo as user_repo
from services import event_service
from utils import env, logger


# ── 1. Конфігурація (.env) ───────────────────────────────────
class TestEnv:
    """Завантаження змінних середовища та ADMIN_IDS."""

    def test_load_env_reads_values(self, tmp_path, monkeypatch):
        # Парсить KEY=VALUE, ігнорує коментарі
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# comment\nBOT_TOKEN=token123\nADMIN_IDS=111,222\n",
            encoding="utf-8",
        )

        class FakePath:
            def __init__(self, *_args, **_kwargs):
                pass

            @property
            def parent(self):
                return type("Mid", (), {"parent": tmp_path})()

        monkeypatch.setattr(env, "Path", FakePath)
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.delenv("ADMIN_IDS", raising=False)

        env.load_env()

        assert env.os.environ.get("BOT_TOKEN") == "token123"
        assert env.os.environ.get("ADMIN_IDS") == "111,222"

    def test_get_admin_ids_parses_multiple(self, monkeypatch):
        monkeypatch.setenv("ADMIN_IDS", "111, 222, abc, 333")

        assert env.get_admin_ids() == {111, 222, 333}

    def test_require_raises_when_missing(self, monkeypatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)

        with pytest.raises(RuntimeError, match="MISSING_KEY"):
            env.require("MISSING_KEY")


# ── 2. Валідація дати та часу ────────────────────────────────
class TestEventParsing:
    """Парсинг і форматування полів події."""

    def test_parse_date_valid(self):
        assert event_service.parse_date("15.06.2026") == date(2026, 6, 15)

    def test_parse_date_invalid_format(self):
        assert event_service.parse_date("2026-06-15") is None
        assert event_service.parse_date("32.13.2026") is None

    def test_parse_time_valid_and_normalized(self):
        assert event_service.parse_time("09:05") == "09:05"
        assert event_service.parse_time("9:05") is None  # потрібен формат HH:MM

    def test_parse_time_out_of_range(self):
        assert event_service.parse_time("25:00") is None
        assert event_service.parse_time("12:60") is None

    def test_format_event_with_optional_fields(self):
        event = {
            "title": "Зустріч",
            "event_date": "2026-06-15",
            "event_time": "14:30",
            "description": "Опис",
        }
        text = event_service.format_event(event, idx=1)

        assert "1." in text
        assert "<b>Зустріч</b>" in text
        assert "15.06.2026" in text
        assert "14:30" in text
        assert "Опис" in text


# ── 3. Бізнес-логіка подій ───────────────────────────────────
class TestEventService:
    """CRUD подій і нагадувань через сервісний шар."""

    async def _create_user_and_event(self, user_id: int = 1001) -> int:
        await user_repo.get_or_create_user(user_id, "tester", "Test User")
        tomorrow = (date.today() + timedelta(days=1)).strftime("%d.%m.%Y")
        ok, err, event_id = await event_service.create_event(
            user_id, "Подія", tomorrow, "10:00", "опис"
        )
        assert ok, err
        return event_id

    async def test_create_event_success(self, test_db):
        user_id = 1001
        await user_repo.get_or_create_user(user_id, "tester", "Test User")
        tomorrow = (date.today() + timedelta(days=1)).strftime("%d.%m.%Y")

        ok, err, event_id = await event_service.create_event(
            user_id, "  Мітинг  ", tomorrow, "09:30", "важливо"
        )

        assert ok is True
        assert err == ""
        assert event_id is not None
        stored = await event_repo.get_event_by_id(event_id, user_id)
        assert stored["title"] == "Мітинг"
        assert stored["event_time"] == "09:30"

    async def test_create_event_rejects_empty_title(self, test_db):
        tomorrow = (date.today() + timedelta(days=1)).strftime("%d.%m.%Y")

        ok, err, event_id = await event_service.create_event(1, "   ", tomorrow, None, None)

        assert ok is False
        assert "порожньою" in err
        assert event_id is None

    async def test_create_event_rejects_past_date(self, test_db):
        yesterday = (date.today() - timedelta(days=1)).strftime("%d.%m.%Y")

        ok, err, _ = await event_service.create_event(1, "Тест", yesterday, None, None)

        assert ok is False
        assert "минулому" in err

    async def test_get_events_today_and_week(self, test_db):
        user_id = 2002
        await user_repo.get_or_create_user(user_id, "tester", "Test User")
        today = date.today().strftime("%d.%m.%Y")
        await event_service.create_event(user_id, "Сьогодні", today, None, None)

        today_events = await event_service.get_events_today(user_id)
        week_events = await event_service.get_events_week(user_id)

        assert len(today_events) == 1
        assert len(week_events) >= 1

    async def test_delete_event_removes_record(self, test_db):
        user_id = 3003
        event_id = await self._create_user_and_event(user_id)

        ok, err = await event_service.delete_event(user_id, event_id)

        assert ok is True
        assert err == ""
        assert await event_repo.get_event_by_id(event_id, user_id) is None

    async def test_delete_event_wrong_user(self, test_db):
        event_id = await self._create_user_and_event(4004)

        ok, err = await event_service.delete_event(9999, event_id)

        assert ok is False
        assert "не знайдено" in err

    async def test_update_event_datetime(self, test_db):
        user_id = 5005
        event_id = await self._create_user_and_event(user_id)
        new_date = (date.today() + timedelta(days=2)).strftime("%d.%m.%Y")

        ok, err = await event_service.update_event_datetime(user_id, event_id, new_date, "11:00")

        assert ok is True
        updated = await event_repo.get_event_by_id(event_id, user_id)
        assert updated["event_date"] == (date.today() + timedelta(days=2)).isoformat()
        assert updated["event_time"] == "11:00"

    async def test_add_reminder_for_future_event(self, test_db):
        user_id = 6006
        event_id = await self._create_user_and_event(user_id)
        event = await event_repo.get_event_by_id(event_id, user_id)

        ok, err = await event_service.add_reminder_for_event(
            event_id, user_id, event["event_date"], event["event_time"], "1hour"
        )

        assert ok is True
        reminders = await reminder_repo.get_reminders_for_event(event_id)
        assert len(reminders) == 1
        assert reminders[0]["reminder_type"] == "1hour"

    async def test_add_reminder_rejects_past_time(self, test_db):
        user_id = 7007
        await user_repo.get_or_create_user(user_id, "tester", "Test User")
        today = date.today().strftime("%d.%m.%Y")
        ok, _, event_id = await event_service.create_event(user_id, "Скоро", today, "23:59", None)
        assert ok

        fail_ok, fail_err = await event_service.add_reminder_for_event(
            event_id, user_id, date.today().isoformat(), "23:59", "1day"
        )

        assert fail_ok is False
        assert "минув" in fail_err

    async def test_update_event_clears_reminders(self, test_db):
        user_id = 8008
        event_id = await self._create_user_and_event(user_id)
        event = await event_repo.get_event_by_id(event_id, user_id)
        await event_service.add_reminder_for_event(
            event_id, user_id, event["event_date"], event["event_time"], "10min"
        )
        new_date = (date.today() + timedelta(days=3)).strftime("%d.%m.%Y")

        await event_service.update_event_datetime(user_id, event_id, new_date, "12:00")

        assert await reminder_repo.get_reminders_for_event(event_id) == []


# ── 4. Репозиторій користувачів ──────────────────────────────
class TestUserRepository:
    """Реєстрація та підрахунок користувачів."""

    async def test_get_or_create_user_idempotent(self, test_db):
        await user_repo.get_or_create_user(9001, "user1", "User One")
        await user_repo.get_or_create_user(9001, "user1", "User One")

        assert await user_repo.get_users_count() == 1
        assert await user_repo.user_exists(9001) is True

    async def test_get_all_users_returns_registered(self, test_db):
        await user_repo.get_or_create_user(9002, "a", "Alice")
        await user_repo.get_or_create_user(9003, "b", "Bob")

        users = await user_repo.get_all_users()

        assert len(users) == 2
        names = {u["full_name"] for u in users}
        assert names == {"Alice", "Bob"}


# ── 5. Репозиторій нагадувань ────────────────────────────────
class TestReminderRepository:
    """Планувальник: прострочені нагадування та позначка sent."""

    async def test_get_due_reminders_and_mark_sent(self, test_db):
        user_id = 10001
        await user_repo.get_or_create_user(user_id, "u", "User")
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        event_id = await event_repo.add_event(user_id, "E", tomorrow, "12:00", None)

        past = datetime.now() - timedelta(minutes=5)
        reminder_id = await reminder_repo.add_reminder(event_id, user_id, past, "custom")

        due = await reminder_repo.get_due_reminders(datetime.now())
        assert any(r["id"] == reminder_id for r in due)

        await reminder_repo.mark_sent(reminder_id)
        due_after = await reminder_repo.get_due_reminders(datetime.now())
        assert all(r["id"] != reminder_id for r in due_after)

    async def test_delete_reminders_for_event(self, test_db):
        user_id = 10002
        await user_repo.get_or_create_user(user_id, "u", "User")
        event_id = await event_repo.add_event(
            user_id, "E", date.today().isoformat(), None, None
        )
        await reminder_repo.add_reminder(
            event_id, user_id, datetime.now() + timedelta(hours=1), "10min"
        )

        await reminder_repo.delete_reminders_for_event(event_id)

        assert await reminder_repo.get_reminders_for_event(event_id) == []


# ── 6. Логування дій ─────────────────────────────────────────
class TestLogger:
    """Запис дій користувача у файл."""

    def test_log_action_writes_entry(self, tmp_path, monkeypatch):
        log_file = tmp_path / "actions.log"
        monkeypatch.setattr(logger, "LOG_FILE", str(log_file))

        logger.log_action(1729483245, "test_action", "detail")

        content = log_file.read_text(encoding="utf-8")
        assert "user=1729483245" in content
        assert "action=test_action" in content
        assert "detail" in content
