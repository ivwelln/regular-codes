import json

import httpx2
import pytest

from app.clients.gamestores import (
    ActivationResult,
    GameStoresClient,
    Player,
    StoreUnavailableError,
)

BASE_URL = "https://shop.test/api/v1"
NOT_LOGGED = {"result": "fail", "message": "Необходима авторизация", "logged": False}


class FakeStore:
    """Отвечает вместо магазина и запоминает присланные запросы."""

    def __init__(self) -> None:
        self.response = httpx2.Response(
            200, json={"result": "fail", "message": "Промокод не найден"}
        )
        self.requests: list[httpx2.Request] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.response


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
async def client(store: FakeStore):
    http = httpx2.AsyncClient(base_url=BASE_URL, transport=httpx2.MockTransport(store.handle))
    async with http:
        yield GameStoresClient(http)


async def test_use_promo_code_sends_code_with_session(client, store) -> None:
    await client.use_promo_code("session-a", "RUST2026")

    request = store.requests[0]
    assert request.method == "POST"
    assert str(request.url) == f"{BASE_URL}/player.usePromoCode"
    assert request.headers["Cookie"] == "SessionShop=session-a"
    assert json.loads(request.content) == {"promocode": "RUST2026"}


async def test_successful_activation(client, store) -> None:
    store.response = httpx2.Response(
        200, json={"result": "success", "messages": ["Вам начислено 100 :currency"]}
    )

    outcome = await client.use_promo_code("session-a", "RUST2026")

    assert outcome.result == ActivationResult.ACTIVATED
    assert outcome.message == "Вам начислено 100 :currency"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"result": "fail", "message": "Промокод не найден"}, ActivationResult.NOT_FOUND),
        ({"result": "fail", "message": "Промокод уже использован"}, ActivationResult.REJECTED),
        (NOT_LOGGED, ActivationResult.SESSION_EXPIRED),
    ],
    ids=["not_found", "rejected", "session_expired"],
)
async def test_failed_activation(client, store, body, expected) -> None:
    store.response = httpx2.Response(200, json=body)

    outcome = await client.use_promo_code("session-a", "RUST2026")

    assert outcome.result == expected
    assert outcome.message == body["message"]


async def test_get_player_returns_profile(client, store) -> None:
    store.response = httpx2.Response(
        200,
        json={
            "result": "success",
            "data": {"steamId": 76561198000000000, "username": "ivan", "balance": 0},
        },
    )

    player = await client.get_player("session-a")

    assert player == Player(steamId="76561198000000000", username="ivan")
    assert store.requests[0].method == "GET"
    assert str(store.requests[0].url) == f"{BASE_URL}/player.info"


async def test_get_player_returns_none_when_session_expired(client, store) -> None:
    store.response = httpx2.Response(200, json=NOT_LOGGED)

    assert await client.get_player("session-a") is None


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(503),
        httpx2.Response(200, text="<html>Проверка браузера</html>"),
        httpx2.Response(200, json={"result": "fail", "maintenance": True}),
    ],
    ids=["overloaded", "protection_page", "maintenance"],
)
async def test_raises_when_store_unavailable(client, store, response) -> None:
    store.response = response

    with pytest.raises(StoreUnavailableError):
        await client.use_promo_code("session-a", "RUST2026")


async def test_raises_on_network_error(store) -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused")

    async with httpx2.AsyncClient(base_url=BASE_URL, transport=httpx2.MockTransport(fail)) as http:
        with pytest.raises(StoreUnavailableError):
            await GameStoresClient(http).use_promo_code("session-a", "RUST2026")


async def test_does_not_leak_cookies_between_accounts(client, store) -> None:
    store.response = httpx2.Response(
        200,
        json={"result": "fail", "message": "Промокод не найден"},
        headers={"Set-Cookie": "PHPSESSID=from-account-a; path=/"},
    )

    await client.use_promo_code("session-a", "RUST2026")
    await client.use_promo_code("session-b", "RUST2026")

    assert store.requests[1].headers["Cookie"] == "SessionShop=session-b"
