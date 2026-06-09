"""QA Етап 4. Ручний чеклист: qa/QA_STAGE4.md"""

from datetime import date, timedelta

import db.event_repo as event_repo
import db.user_repo as user_repo
from handlers.keyboards import main_menu, stats_menu
from services import stats_service


class TestQaStage4Aggregation:
    def test_count_by_day_fills_gaps(self):
        today = date.today()
        events = [{"event_date": today.isoformat()}]
        start = today - timedelta(days=2)

        result = stats_service.count_by_day(events, start, today)

        assert len(result) == 3
        assert result[today.isoformat()] == 1

    def test_count_by_hour(self):
        events = [
            {"event_time": "09:00"},
            {"event_time": "09:30"},
            {"event_time": "14:00"},
        ]
        assert stats_service.count_by_hour(events) == {9: 2, 14: 1}

    def test_count_by_weekday(self):
        d = date.today().isoformat()
        events = [{"event_date": d}, {"event_date": d}]
        wd = date.today().weekday()
        assert stats_service.count_by_weekday(events)[wd] == 2


class TestQaStage4Charts:
    async def test_generate_returns_none_without_events(self, test_db):
        result = await stats_service.generate_stats_image(8001, 7)
        assert result is None

    async def test_generate_creates_png(self, test_db, tmp_path, monkeypatch):
        monkeypatch.setattr(stats_service, "TMP_DIR", tmp_path)
        user_id = 8002
        await user_repo.get_or_create_user(user_id, "u", "User")
        today = date.today().isoformat()
        await event_repo.add_event(user_id, "A", today, "10:00", None)

        path = await stats_service.generate_stats_image(user_id, 7)

        assert path is not None
        assert path.exists()
        assert path.suffix == ".png"
        assert path.stat().st_size > 0


class TestQaStage4Ui:
    def test_main_menu_has_stats_button(self):
        callbacks = [
            btn.callback_data
            for row in main_menu().inline_keyboard
            for btn in row
        ]
        assert "stats_menu" in callbacks

    def test_stats_menu_periods(self):
        callbacks = [
            btn.callback_data
            for row in stats_menu().inline_keyboard
            for btn in row
        ]
        assert "stats_week" in callbacks
        assert "stats_month" in callbacks

    def test_stats_router_registered(self):
        from handlers import stats

        assert len(stats.router.callback_query.handlers) >= 2


class TestQaStage4UiHelper:
    async def test_edit_or_answer_on_photo_sends_new_message(self):
        from unittest.mock import AsyncMock, MagicMock

        from handlers.ui import edit_or_answer

        msg = MagicMock()
        msg.text = None
        msg.photo = [MagicMock()]
        msg.document = None
        msg.delete = AsyncMock()
        msg.answer = AsyncMock()

        cb = MagicMock()
        cb.message = msg

        await edit_or_answer(cb, "Меню", reply_markup=None)

        msg.delete.assert_awaited_once()
        msg.answer.assert_awaited_once_with("Меню", reply_markup=None)
