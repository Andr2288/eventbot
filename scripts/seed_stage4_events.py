"""
Сідові події для тесту етапу 4 (статистика).

Використання:
  python scripts/seed_stage4_events.py <telegram_id>

telegram_id — твій ID з @userinfobot (той самий, що в ADMIN_IDS).
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.env import load_env

load_env()

from db.database import init_db
import db.event_repo as event_repo
import db.user_repo as user_repo

# (днів тому від сьогодні, назва, час або None)
SEED_EVENTS = [
    (0,  "Лекція з програмування", "10:00"),
    (0,  "Обід з друзями", "13:00"),
    (1,  "Зустріч з куратором", "09:00"),
    (1,  "Спортзал", "18:30"),
    (2,  "Консультація", "11:00"),
    (3,  "Диплом — правки", "14:00"),
    (3,  "Покупки", "17:00"),
    (5,  "Лабораторна робота", "10:30"),
    (7,  "Звіт по практиці", "09:30"),
    (7,  "Вебінар", "15:00"),
    (10, "Репетитор", "16:00"),
    (12, "Стоматолог", "11:30"),
    (14, "Захист проєкту (репетиція)", "10:00"),
    (14, "Зустріч з викладачем", "14:00"),
    (18, "Курсові завдання", None),
    (20, "Бібліотека", "12:00"),
    (22, "Онлайн-курс", "19:00"),
    (25, "Планерка", "09:00"),
    (25, "Планерка", "09:00"),  # повтор — для регулярності на графіку
    (28, "Семінар", "13:30"),
    # майбутні (для повноти тижневого перегляду)
    ( -2, "Підготовка до захисту", "10:00"),
    ( -5, "Фінальна зустріч", "15:00"),
]


async def seed(user_id: int) -> int:
    await init_db()
    await user_repo.get_or_create_user(user_id, "seed_user", "Seed Tester")

    today = date.today()
    created = 0
    for days_ago, title, event_time in SEED_EVENTS:
        event_date = (today - timedelta(days=days_ago)).isoformat()
        await event_repo.add_event(user_id, title, event_date, event_time, "seed stage4")
        created += 1

    return created


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        print(__doc__)
        sys.exit(1)

    user_id = int(sys.argv[1])
    count = asyncio.run(seed(user_id))
    print(f"Додано {count} сідових подій для user_id={user_id}")
    print("Перезапускати бота не потрібно. Відкрий «Статистика» в Telegram.")


if __name__ == "__main__":
    main()
