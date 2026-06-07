"""Сервіс подій — валідація та бізнес-логіка."""

import re
from datetime import date, datetime, timedelta
from typing import Optional

import db.event_repo as event_repo
import db.reminder_repo as reminder_repo

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")

REMINDER_OPTIONS = {
    "10min":  ("За 10 хвилин", timedelta(minutes=10)),
    "1hour":  ("За 1 годину",  timedelta(hours=1)),
    "1day":   ("За 1 день",    timedelta(days=1)),
}


def parse_date(raw: str) -> date | None:
    if not DATE_RE.match(raw.strip()):
        return None
    try:
        return datetime.strptime(raw.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def parse_time(raw: str) -> str | None:
    raw = raw.strip()
    if not TIME_RE.match(raw):
        return None
    h, m = int(raw[:2]), int(raw[3:])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return f"{h:02d}:{m:02d}"


def format_event(event: dict, idx: int | None = None) -> str:
    prefix = f"{idx}. " if idx else ""
    d = datetime.strptime(event["event_date"], "%Y-%m-%d").strftime("%d.%m.%Y")
    time_str = f" о {event['event_time']}" if event.get("event_time") else ""
    desc = f"\n   📝 {event['description']}" if event.get("description") else ""
    return f"{prefix}📅 <b>{event['title']}</b>\n   {d}{time_str}{desc}"


async def create_event(
    user_id: int,
    title: str,
    date_str: str,
    time_str: Optional[str],
    description: Optional[str],
) -> tuple[bool, str, int | None]:
    """Створити подію. Повертає (success, error, event_id)."""
    if not title.strip():
        return False, "Назва події не може бути порожньою.", None
    parsed = parse_date(date_str)
    if not parsed:
        return False, "Невірний формат дати. Використовуй ДД.ММ.РРРР", None
    if parsed < date.today():
        return False, "Дата не може бути в минулому.", None

    db_date = parsed.isoformat()
    event_id = await event_repo.add_event(
        user_id, title.strip(), db_date, time_str, description
    )
    return True, "", event_id


async def add_reminder_for_event(
    event_id: int,
    user_id: int,
    event_date: str,
    event_time: Optional[str],
    reminder_type: str,
    custom_minutes: int | None = None,
) -> tuple[bool, str]:
    """Додати нагадування до події."""
    # Визначити час події
    if event_time:
        h, m = int(event_time[:2]), int(event_time[3:])
        event_dt = datetime.strptime(event_date, "%Y-%m-%d").replace(hour=h, minute=m, second=0)
    else:
        # Без часу — нагадуємо о 9:00 ранку
        event_dt = datetime.strptime(event_date, "%Y-%m-%d").replace(hour=9, minute=0, second=0)

    if reminder_type == "custom" and custom_minutes is not None:
        delta = timedelta(minutes=custom_minutes)
    elif reminder_type in REMINDER_OPTIONS:
        _, delta = REMINDER_OPTIONS[reminder_type]
    else:
        return False, "Невідомий тип нагадування."

    remind_at = event_dt - delta
    if remind_at < datetime.now():
        return False, "Час нагадування вже минув."

    await reminder_repo.add_reminder(event_id, user_id, remind_at, reminder_type)
    return True, ""


async def get_events_today(user_id: int) -> list[dict]:
    day = date.today().isoformat()
    return await event_repo.get_events_by_day(user_id, day)


async def get_events_week(user_id: int) -> list[dict]:
    today = date.today()
    end = today + timedelta(days=6)
    return await event_repo.get_events_by_week(user_id, today.isoformat(), end.isoformat())


async def get_all_events(user_id: int) -> list[dict]:
    return await event_repo.get_all_events(user_id)


async def delete_event(user_id: int, event_id: int) -> tuple[bool, str]:
    await reminder_repo.delete_reminders_for_event(event_id)
    ok = await event_repo.delete_event(event_id, user_id)
    return (True, "") if ok else (False, "Подію не знайдено.")


async def update_event_datetime(
    user_id: int,
    event_id: int,
    date_str: str,
    time_str: Optional[str],
) -> tuple[bool, str]:
    ev = await event_repo.get_event_by_id(event_id, user_id)
    if not ev:
        return False, "Подію не знайдено."
    parsed = parse_date(date_str)
    if not parsed:
        return False, "Невірний формат дати."
    ok = await event_repo.update_event(
        event_id, user_id, ev["title"], parsed.isoformat(), time_str, ev.get("description")
    )
    if ok:
        # Скидаємо старі нагадування при зміні часу
        await reminder_repo.delete_reminders_for_event(event_id)
    return (True, "") if ok else (False, "Помилка оновлення.")
