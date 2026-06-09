"""QA Етап 2. Ручний чеклист: qa/QA_STAGE2.md"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from handlers.keyboards import main_menu
from services import speech_service
from services.openai_client import get_client


class TestQaStage2Speech:
    def test_transcribe_requires_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            get_client()

    async def test_transcribe_returns_text(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(speech_service, "TMP_DIR", tmp_path)

        fake_result = MagicMock()
        fake_result.text = "  Зустріч з викладачем  "

        fake_audio = MagicMock()
        fake_audio.transcriptions.create = AsyncMock(return_value=fake_result)

        fake_client = MagicMock()
        fake_client.audio = fake_audio
        monkeypatch.setattr(speech_service, "get_client", lambda: fake_client)

        bot = AsyncMock()
        bot.get_file = AsyncMock(return_value=MagicMock(file_path="voice/file.ogg"))

        async def fake_download(_path, dest):
            dest.write_bytes(b"fake-audio")

        bot.download_file = fake_download

        text = await speech_service.transcribe_telegram_voice(bot, "voice123")

        assert text == "Зустріч з викладачем"
        fake_audio.transcriptions.create.assert_awaited_once()
        call_kwargs = fake_audio.transcriptions.create.await_args.kwargs
        assert call_kwargs["model"] == "whisper-1"
        assert call_kwargs["language"] == "uk"


class TestQaStage2Ui:
    def test_main_menu_has_voice_button(self):
        callbacks = [
            btn.callback_data
            for row in main_menu().inline_keyboard
            for btn in row
        ]
        assert "event_create_voice" in callbacks

    def test_voice_router_registered(self):
        from handlers import voice

        assert len(voice.router.message.handlers) >= 1
        assert len(voice.router.callback_query.handlers) >= 1
