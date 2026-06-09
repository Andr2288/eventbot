"""Візуалізація статистики подій (matplotlib)."""

from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import db.event_repo as event_repo

TMP_DIR = Path(__file__).resolve().parent.parent / "tmp"
WEEKDAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def _day_range(days: int) -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    return start, end


def count_by_day(events: list[dict], start: date, end: date) -> dict[str, int]:
    counts = Counter(ev["event_date"] for ev in events)
    result: dict[str, int] = {}
    current = start
    while current <= end:
        key = current.isoformat()
        result[key] = counts.get(key, 0)
        current += timedelta(days=1)
    return result


def count_by_hour(events: list[dict]) -> dict[int, int]:
    hours: list[int] = []
    for ev in events:
        t = ev.get("event_time")
        if t:
            hours.append(int(t[:2]))
    return dict(Counter(hours))


def count_by_weekday(events: list[dict]) -> dict[int, int]:
    counts = Counter(
        datetime.strptime(ev["event_date"], "%Y-%m-%d").weekday() for ev in events
    )
    return {i: counts.get(i, 0) for i in range(7)}


def _plot_stats(events: list[dict], start: date, end: date, days: int, out_path: Path) -> None:
    by_day = count_by_day(events, start, end)
    by_hour = count_by_hour(events)
    by_weekday = count_by_weekday(events)

    labels_day = [
        datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m") for d in by_day.keys()
    ]
    fig, axes = plt.subplots(3, 1, figsize=(10, 9))

    axes[0].bar(labels_day, list(by_day.values()), color="#4C78A8")
    axes[0].set_title("Події по днях")
    axes[0].tick_params(axis="x", rotation=45)

    if by_hour:
        hours = sorted(by_hour.keys())
        axes[1].bar(hours, [by_hour[h] for h in hours], color="#F58518")
        axes[1].set_title("Розподіл по годинах")
        axes[1].set_xlabel("Година")
    else:
        axes[1].text(0.5, 0.5, "Немає подій з часом", ha="center", va="center")
        axes[1].set_axis_off()

    axes[2].bar(WEEKDAY_LABELS, [by_weekday[i] for i in range(7)], color="#54A24B")
    axes[2].set_title("Навантаження по днях тижня")

    fig.suptitle(f"Статистика за {days} дн.", fontsize=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


async def generate_stats_image(user_id: int, days: int) -> Path | None:
    start, end = _day_range(days)
    events = await event_repo.get_events_in_range(user_id, start.isoformat(), end.isoformat())
    if not events:
        return None

    TMP_DIR.mkdir(exist_ok=True)
    out_path = TMP_DIR / f"stats_{user_id}_{days}d.png"
    _plot_stats(events, start, end, days, out_path)
    return out_path
