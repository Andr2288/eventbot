"""QA Етап 3. Ручний чеклист: qa/QA_STAGE3.md"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import db.event_repo as event_repo
import db.user_repo as user_repo
from handlers.keyboards import main_menu
from services import recommend_service
from services.openai_client import get_client


class TestQaStage3Recommend:
    async def test_no_data_returns_hint_without_api(self, test_db, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(recommend_service, "get_client", lambda: fake_client)

        text = await recommend_service.get_recommendations(7001)

        assert "недостатньо даних" in text.lower()
        fake_client.chat.completions.create.assert_not_called()

    async def test_gpt_recommendations_with_history(self, test_db, monkeypatch):
        user_id = 7002
        await user_repo.get_or_create_user(user_id, "u", "User")
        await event_repo.add_event(user_id, "Зустріч", "2099-06-01", "10:00", None)

        fake_msg = MagicMock(content="1. Плануй о 10:00\n2. Повтори зустріч щотижня")
        fake_choice = MagicMock(message=fake_msg)
        fake_resp = MagicMock(choices=[fake_choice])

        fake_chat = MagicMock()
        fake_chat.completions.create = AsyncMock(return_value=fake_resp)
        fake_client = MagicMock(chat=fake_chat)
        monkeypatch.setattr(recommend_service, "get_client", lambda: fake_client)

        text = await recommend_service.get_recommendations(user_id)

        assert "10:00" in text or "зустріч" in text.lower()
        fake_chat.completions.create.assert_awaited_once()

    def test_openai_client_requires_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            get_client()


class TestQaStage3Ui:
    def test_main_menu_has_recommendations_button(self):
        callbacks = [
            btn.callback_data
            for row in main_menu().inline_keyboard
            for btn in row
        ]
        assert "recommendations" in callbacks

    def test_recommendations_router_registered(self):
        from handlers import recommendations

        assert len(recommendations.router.callback_query.handlers) >= 1
