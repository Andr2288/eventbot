"""Рекомендації на основі історії подій (OpenAI GPT)."""

import os
from datetime import date, datetime

import db.event_repo as event_repo
from services.openai_client import get_client

SYSTEM_PROMPT = """Ти помічник планувальника задач. На основі історії подій користувача дай короткі поради українською:
1) оптимальний час для нових справ (за звичним розкладом);
2) можливі регулярні задачі, які варто повторити;
3) короткий план на сьогодні.
Відповідь: до 10 рядків, без markdown, простий текст з нумерацією 1-3."""


def _fmt_event(ev: dict) -> str:
    d = datetime.strptime(ev["event_date"], "%Y-%m-%d").strftime("%d.%m.%Y")
    t = ev.get("event_time") or "без часу"
    status = ev.get("status", "pending")
    return f"- {ev['title']} | {d} {t} | {status}"


def _build_context(history: list[dict], today_events: list[dict], upcoming: list[dict]) -> str:
    today = date.today().strftime("%d.%m.%Y")
    lines = [f"Сьогодні: {today}", "", "Події на сьогодні:"]
    lines += [_fmt_event(e) for e in today_events] or ["- немає"]
    lines += ["", "Майбутні події:"]
    lines += [_fmt_event(e) for e in upcoming[:15]] or ["- немає"]
    lines += ["", "Історія (останні події):"]
    lines += [_fmt_event(e) for e in history[:30]] or ["- немає"]
    return "\n".join(lines)


async def get_recommendations(user_id: int) -> str:
    history = await event_repo.get_events_history(user_id, limit=30)
    today = date.today().isoformat()
    today_events = await event_repo.get_events_by_day(user_id, today)
    upcoming = await event_repo.get_all_events(user_id)

    if not history and not today_events and not upcoming:
        return (
            "Поки недостатньо даних.\n"
            "Створи кілька подій — і я запропоную час, регулярні справи та план дня."
        )

    context = _build_context(history, today_events, upcoming)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    response = await get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        max_tokens=400,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()
