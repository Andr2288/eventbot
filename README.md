# EventBot 📅

Telegram-бот для планування подій та нагадувань.

## Можливості

- **Створення подій** — назва, дата, час (опц.), опис (опц.)
- **Нагадування** — за 10 хв / 1 год / 1 день / власний час
- **Перегляд** — на сьогодні, на тиждень, всі майбутні події
- **Редагування** — зміна дати та часу події
- **Видалення** — видаляє подію разом із нагадуваннями
- **Адмін-панель** — кількість користувачів, список, логи, резервна копія БД

## Стек

- Python 3.11+
- [aiogram 3](https://docs.aiogram.dev/) — Telegram Bot API
- SQLite + [aiosqlite](https://aiosqlite.omnilib.dev/)
- FSM (Finite State Machine) для діалогів

## Структура

```
eventbot/
├── main.py                  # Точка входу
├── .env                     # Токен та налаштування
├── requirements.txt
├── db/
│   ├── database.py          # Ініціалізація SQLite, таблиці
│   ├── user_repo.py         # CRUD користувачів
│   ├── event_repo.py        # CRUD подій
│   └── reminder_repo.py     # CRUD нагадувань
├── services/
│   └── event_service.py     # Бізнес-логіка (валідація, форматування)
├── handlers/
│   ├── registration.py      # /start
│   ├── commands.py          # /help /today /week /all /admin
│   ├── callbacks.py         # Всі inline-кнопки + FSM
│   └── keyboards.py         # Всі клавіатури
├── scheduler/
│   └── notifier.py          # Автоматичні нагадування (кожні 30 сек)
└── utils/
    ├── env.py               # Завантаження .env
    └── logger.py            # Логування дій у файл logs/actions.log
```

## Таблиці БД

| Таблиця   | Поля                                                          |
|-----------|---------------------------------------------------------------|
| users     | id, telegram_id, username, full_name, created_at              |
| events    | id, user_id, title, event_date, event_time, description, created_at |
| reminders | id, event_id, user_id, remind_at, sent, reminder_type         |

## Запуск

```bash
# 1. Встановити залежності
pip install -r requirements.txt

# 2. Заповнити .env
#    BOT_TOKEN — токен від @BotFather
#    ADMIN_IDS — твій Telegram ID (дізнайся у @userinfobot)

# 3. Запустити
python main.py
```

## Налаштування адміна

У файлі `.env`:
```
ADMIN_IDS=123456789
# або кілька:
ADMIN_IDS=123456789,987654321
```

Потім у боті: команда `/admin`.

## Тестування

- **User stories + QA чекліст (64 тест-кейси):** [QA_TEST_PLAN.md](QA_TEST_PLAN.md)
- Швидкий smoke-test (~15 хв) — в кінці того ж файлу

### Юніт-тести (pytest)

```bash
pip install -r requirements.txt
pytest -v
```
