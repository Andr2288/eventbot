"""Спільні фікстури: тимчасова SQLite БД для ізольованих тестів."""

import pytest

import db.database as database


@pytest.fixture
async def test_db(tmp_path, monkeypatch):
    """Підміняє eventbot.db на тимчасовий файл і ініціалізує таблиці."""
    db_file = tmp_path / "test_eventbot.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    await database.init_db()
    return db_file
