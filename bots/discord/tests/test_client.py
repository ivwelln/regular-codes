from datetime import timedelta
from types import SimpleNamespace

import discord
import httpx2
import pytest

from bot.client import PromoBot

CHANNEL_ID = 100


class FakeBackend:
    """Запоминает отправленные сообщения вместо запросов к backend."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.error: Exception | None = None

    async def send_message(self, external_id: str, text: str) -> list[str]:
        if self.error is not None:
            raise self.error
        self.sent.append((external_id, text))
        return ["RUST2026"]


class FakeChannel:
    """Отдаёт заданную историю сообщений и запоминает, как её запросили."""

    def __init__(self) -> None:
        self.messages: list[SimpleNamespace] = []
        self.error: Exception | None = None
        self.history_kwargs: dict = {}

    async def history(self, **kwargs):
        self.history_kwargs = kwargs
        if self.error is not None:
            raise self.error
        for message in self.messages:
            yield message


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def bot(backend: FakeBackend) -> PromoBot:
    return PromoBot(backend, frozenset({CHANNEL_ID}), catch_up_delay=0)


@pytest.fixture
def channel(bot: PromoBot, monkeypatch) -> FakeChannel:
    channel = FakeChannel()
    monkeypatch.setattr(bot, "get_channel", {CHANNEL_ID: channel}.get)
    return channel


def make_message(message_id: int = 555, channel_id: int = CHANNEL_ID, content: str = "Промокод RUST2026"):
    return SimpleNamespace(
        id=message_id, channel=SimpleNamespace(id=channel_id), content=content, embeds=[]
    )


def test_requests_message_content(bot) -> None:
    assert bot.intents.message_content


async def test_sends_message_from_watched_channel(bot, backend) -> None:
    await bot.on_message(make_message())

    assert backend.sent == [("555", "Промокод RUST2026")]


async def test_ignores_other_channels(bot, backend) -> None:
    await bot.on_message(make_message(channel_id=200))

    assert backend.sent == []


async def test_ignores_message_without_text(bot, backend) -> None:
    await bot.on_message(make_message(content=""))

    assert backend.sent == []


async def test_survives_backend_error(bot, backend, caplog) -> None:
    backend.error = httpx2.ConnectError("backend is down")

    await bot.on_message(make_message())

    assert "message 555 was not sent to backend" in caplog.text


async def test_catches_up_on_history_after_login(bot, backend, channel) -> None:
    channel.messages = [make_message(1, content="Код OLD1"), make_message(2, content="Код OLD2")]

    await bot.on_ready()

    assert backend.sent == [("1", "Код OLD1"), ("2", "Код OLD2")]


async def test_reads_history_of_last_days_from_oldest(bot, channel) -> None:
    await bot.on_ready()

    week_ago = discord.utils.utcnow() - timedelta(days=7)
    assert abs(channel.history_kwargs["after"] - week_ago) < timedelta(seconds=5)
    assert channel.history_kwargs["limit"] is None
    assert channel.history_kwargs["oldest_first"] is True


async def test_skips_unavailable_channel(bot, backend, monkeypatch, caplog) -> None:
    monkeypatch.setattr(bot, "get_channel", lambda channel_id: None)

    await bot.on_ready()

    assert backend.sent == []
    assert f"channel {CHANNEL_ID} is not available" in caplog.text


async def test_survives_history_error(bot, channel, caplog) -> None:
    response = SimpleNamespace(status=403, reason="Forbidden")
    channel.error = discord.Forbidden(response, "Missing Access")

    await bot.on_ready()

    assert f"history of channel {CHANNEL_ID} was not read" in caplog.text
