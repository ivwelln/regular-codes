import pytest
from pydantic import ValidationError

from bot.config import Settings


@pytest.fixture(autouse=True)
def token(monkeypatch) -> None:
    monkeypatch.setenv("BOT_DISCORD_TOKEN", "test-token")


def test_reads_channel_ids_from_json(monkeypatch) -> None:
    monkeypatch.setenv("BOT_CHANNEL_IDS", "[1234567890123456789, 42]")

    assert Settings().channel_ids == {1234567890123456789, 42}


def test_requires_at_least_one_channel(monkeypatch) -> None:
    monkeypatch.setenv("BOT_CHANNEL_IDS", "[]")

    with pytest.raises(ValidationError):
        Settings()
