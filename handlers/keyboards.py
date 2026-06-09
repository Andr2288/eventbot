"""Inline-клавіатури бота."""

import calendar
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Створити подію",    callback_data="event_create")
    kb.button(text="🎤 Голосова подія",    callback_data="event_create_voice")
    kb.button(text="🔍 Переглянути події", callback_data="events_view")
    kb.button(text="✏️ Редагувати подію",  callback_data="event_edit_menu")
    kb.button(text="🗑 Видалити подію",    callback_data="event_delete_menu")
    kb.button(text="🔔 Нагадування",       callback_data="reminders_menu")
    kb.button(text="💡 Рекомендації",      callback_data="recommendations")
    kb.button(text="⚙️ Налаштування",    callback_data="settings_menu")
    kb.button(text="ℹ️ Довідка",           callback_data="help")
    kb.adjust(1)
    return kb.as_markup()


def settings_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Видалити всі події",      callback_data="settings_del_events")
    kb.button(text="🔕 Очистити нагадування",    callback_data="settings_clear_reminders")
    kb.button(text="❌ Видалити акаунт",         callback_data="settings_del_account")
    kb.button(text="◀️ Головне меню",            callback_data="menu_main")
    kb.adjust(1)
    return kb.as_markup()


def events_view_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📆 На сьогодні",  callback_data="view_today")
    kb.button(text="🗓 На тиждень",   callback_data="view_week")
    kb.button(text="📋 Всі події",    callback_data="view_all")
    kb.button(text="◀️ Назад",        callback_data="menu_main")
    kb.adjust(1)
    return kb.as_markup()


def reminder_type_keyboard(event_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏰ За 10 хвилин", callback_data=f"rem_10min_{event_id}")
    kb.button(text="🕐 За 1 годину",  callback_data=f"rem_1hour_{event_id}")
    kb.button(text="📅 За 1 день",    callback_data=f"rem_1day_{event_id}")
    kb.button(text="✏️ Власний час",  callback_data=f"rem_custom_{event_id}")
    kb.button(text="◀️ Назад",        callback_data="menu_main")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def events_list_keyboard(events: list[dict], prefix: str) -> InlineKeyboardMarkup:
    """Список подій у вигляді кнопок для вибору."""
    kb = InlineKeyboardBuilder()
    for i, ev in enumerate(events, 1):
        d = ev["event_date"].replace("-", ".")
        label = f"{i}. {ev['title']} ({d})"
        kb.button(text=label[:40], callback_data=f"{prefix}_{ev['id']}")
    kb.button(text="◀️ Назад", callback_data="menu_main")
    kb.adjust(1)
    return kb.as_markup()


def back_to_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Головне меню", callback_data="menu_main")
    kb.adjust(1)
    return kb.as_markup()


def skip_or_back(back: str = "menu_main") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏭ Пропустити",    callback_data="skip_input")
    kb.button(text="◀️ Скасувати",    callback_data=back)
    kb.adjust(2)
    return kb.as_markup()


def confirm_keyboard(yes_data: str, no_data: str = "menu_main") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Так", callback_data=yes_data)
    kb.button(text="❌ Ні",  callback_data=no_data)
    kb.adjust(2)
    return kb.as_markup()


def calendar_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    MONTHS = ["", "Січень","Лютий","Березень","Квітень","Травень","Червень",
               "Липень","Серпень","Вересень","Жовтень","Листопад","Грудень"]
    kb = InlineKeyboardBuilder()
    # Навігація
    kb.button(text="◀",  callback_data=f"cal_prev_{year}_{month}")
    kb.button(text=f"{MONTHS[month]} {year}", callback_data="cal_ignore")
    kb.button(text="▶",  callback_data=f"cal_next_{year}_{month}")
    # Дні тижня
    for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Нд"]:
        kb.button(text=d, callback_data="cal_ignore")
    today = date.today()
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        for day in week:
            if day == 0:
                kb.button(text=" ", callback_data="cal_ignore")
            else:
                d = date(year, month, day)
                if d < today:
                    kb.button(text=str(day), callback_data="cal_ignore")
                else:
                    kb.button(text=str(day), callback_data=f"cal_pick_{year}_{month}_{day}")
    kb.button(text="◀️ Скасувати", callback_data="menu_main")
    kb.adjust(3, 7, *[7]*len(cal), 1)
    return kb.as_markup()


def time_keyboard(step: str, h: int = 9, m: int = 0) -> InlineKeyboardMarkup:
    """Picker для вибору часу події."""
    kb = InlineKeyboardBuilder()
    # Заголовок + поточне значення
    kb.button(text=f"⏰ {h:02d}:{m:02d}", callback_data="cal_ignore")
    kb.button(text="── Година ──", callback_data="cal_ignore")
    # Години по 6
    for hour in range(0, 24):
        mark = "·" if hour == h else ""
        kb.button(text=f"{mark}{hour:02d}{mark}", callback_data=f"time_h_{step}_{hour}_{m}")
    kb.button(text="── Хвилина ──", callback_data="cal_ignore")
    for minute in range(0, 60, 5):
        mark = "·" if minute == m else ""
        kb.button(text=f"{mark}{minute:02d}{mark}", callback_data=f"time_m_{step}_{h}_{minute}")
    kb.button(text=f"✅ Підтвердити {h:02d}:{m:02d}", callback_data=f"time_confirm_{step}_{h}_{m}")
    kb.button(text="⏭ Без часу", callback_data=f"time_skip_{step}")
    kb.adjust(1, 1, 6, 6, 6, 6, 1, 6, 6, 1, 1)
    return kb.as_markup()


# ── Адмін ──────────────────────────────────────────────────
def admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Кількість користувачів", callback_data="admin_users")
    kb.button(text="📊 Список користувачів",   callback_data="admin_users_list")
    kb.button(text="💾 Резервна копія БД",     callback_data="admin_backup")
    kb.button(text="📋 Логи дій",              callback_data="admin_logs")
    kb.button(text="◀️ Назад",                 callback_data="menu_main")
    kb.adjust(1)
    return kb.as_markup()
