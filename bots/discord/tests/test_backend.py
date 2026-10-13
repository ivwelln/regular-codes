import json

import httpx2
import pytest

from bot.backend import MAX_TEXT_LENGTH, BackendClient

BASE_URL = "http://backend.test/api/v1"


class FakeBackend:
    """Отвечает вместо backend и запоминает присланные запросы."""

    def __init__(self) -> None:
        self.response = httpx2.Response(
            200, json={"id": 1, "status": "processed", "codes": ["RUST2026"]}
        )
        self.requests: list[httpx2.Request] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.response


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
async def client(backend: FakeBackend):
    http = httpx2.AsyncClient(base_url=BASE_URL, transport=httpx2.MockTransport(backend.handle))
    async with http:
        yield BackendClient(http)


async def test_sends_message_and_returns_codes(client, backend) -> None:
    codes = await client.send_message("123", "Промокод RUST2026")

    assert codes == ["RUST2026"]
    [request] = backend.requests
    assert request.method == "POST"
    assert str(request.url) == f"{BASE_URL}/messages"
    assert json.loads(request.content) == {
        "source": "discord",
        "external_id": "123",
        "text": "Промокод RUST2026",
    }


async def test_cuts_too_long_text(client, backend) -> None:
    await client.send_message("123", "x" * (MAX_TEXT_LENGTH + 100))

    assert len(json.loads(backend.requests[0].content)["text"]) == MAX_TEXT_LENGTH


async def test_raises_when_backend_fails(client, backend) -> None:
    backend.response = httpx2.Response(500)

    with pytest.raises(httpx2.HTTPStatusError):
        await client.send_message("123", "Промокод RUST2026")
