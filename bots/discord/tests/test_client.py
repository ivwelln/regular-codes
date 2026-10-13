from types import SimpleNamespace

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


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def bot(backend: FakeBackend) -> PromoBot:
    return PromoBot(backend, frozenset({CHANNEL_ID}))


def make_message(channel_id: int = CHANNEL_ID, content: str = "Промокод RUST2026"):
    return SimpleNamespace(
        id=555, channel=SimpleNamespace(id=channel_id), content=content, embeds=[]
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
