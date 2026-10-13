import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_promo_extractor,
    get_session,
    get_session_cipher,
    get_session_factory,
    get_store,
)
from app.clients.gamestores import ActivationOutcome, ActivationResult
from app.core.crypto import SessionCipher
from app.main import app
from app.models import Account, Activation, ActivationStatus, Message, MessageStatus, PromoCode
from app.services.promo_extractor import PromoExtractionError


class FakeExtractor:
    """Возвращает заданные коды вместо обращения к нейросети."""

    def __init__(self, codes: list[str] | None = None) -> None:
        self.codes = codes or []
        self.error: Exception | None = None
        self.calls: list[str] = []

    async def extract(self, text: str) -> list[str]:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return self.codes


class FakeStore:
    """Активирует любой код и запоминает, какие коды пробовали."""

    def __init__(self) -> None:
        self.codes: list[str] = []

    async def use_promo_code(self, session: str, code: str) -> ActivationOutcome:
        self.codes.append(code)
        return ActivationOutcome(ActivationResult.ACTIVATED, "ok")


@pytest.fixture
def extractor() -> FakeExtractor:
    return FakeExtractor()


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def cipher() -> SessionCipher:
    return SessionCipher(Fernet.generate_key().decode())


@pytest.fixture
def api(
    client: AsyncClient,
    db_session: AsyncSession,
    db_session_factory,
    extractor: FakeExtractor,
    store: FakeStore,
    cipher: SessionCipher,
) -> AsyncClient:
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_promo_extractor] = lambda: extractor
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_session_cipher] = lambda: cipher
    return client


@pytest.fixture
async def account(db_session: AsyncSession, cipher: SessionCipher) -> Account:
    account = Account(steam_id="1", username="ivan", encrypted_session=cipher.encrypt("session"))
    db_session.add(account)
    await db_session.commit()
    return account


def message_payload(external_id: str = "1", text: str = "Промокод RUST2026") -> dict:
    return {"source": "discord", "external_id": external_id, "text": text}


async def test_saves_message_and_found_codes(api, db_session, extractor) -> None:
    extractor.codes = ["RUST2026"]

    response = await api.post("/api/v1/messages", json=message_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["codes"] == ["RUST2026"]

    message = await db_session.get(Message, body["id"])
    assert message.text == "Промокод RUST2026"
    assert message.status == MessageStatus.PROCESSED
    codes = await db_session.scalars(
        select(PromoCode.code).where(PromoCode.message_id == message.id)
    )
    assert list(codes) == ["RUST2026"]


async def test_message_without_codes_is_processed(api, extractor) -> None:
    response = await api.post("/api/v1/messages", json=message_payload(text="Вайп в пятницу"))

    assert response.json()["status"] == "processed"
    assert response.json()["codes"] == []


async def test_repeated_message_is_not_checked_again(api, extractor) -> None:
    extractor.codes = ["RUST2026"]
    first = await api.post("/api/v1/messages", json=message_payload())

    second = await api.post("/api/v1/messages", json=message_payload())

    assert second.json() == first.json()
    assert len(extractor.calls) == 1


async def test_message_is_failed_when_extractor_unavailable(api, db_session, extractor) -> None:
    extractor.error = PromoExtractionError("Яндекс недоступен")

    response = await api.post("/api/v1/messages", json=message_payload())

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["codes"] == []
    message = await db_session.get(Message, response.json()["id"])
    assert message.status == MessageStatus.FAILED


async def test_failed_message_is_checked_again(api, extractor) -> None:
    extractor.error = PromoExtractionError("Яндекс недоступен")
    first = await api.post("/api/v1/messages", json=message_payload())
    extractor.error = None
    extractor.codes = ["RUST2026"]

    second = await api.post("/api/v1/messages", json=message_payload())

    assert second.json()["id"] == first.json()["id"]
    assert second.json()["status"] == "processed"
    assert second.json()["codes"] == ["RUST2026"]
    assert len(extractor.calls) == 2


@pytest.mark.parametrize(
    "payload",
    [
        {"source": "discord", "external_id": "1", "text": ""},
        {"source": "discord", "external_id": "", "text": "Промокод RUST2026"},
        {"source": "discord", "text": "Промокод RUST2026"},
    ],
    ids=["empty_text", "empty_external_id", "missing_external_id"],
)
async def test_rejects_invalid_payload(api, extractor, payload) -> None:
    response = await api.post("/api/v1/messages", json=payload)

    assert response.status_code == 422
    assert extractor.calls == []


async def test_found_codes_are_activated_in_background(api, db_session, extractor, store, account):
    extractor.codes = ["RUST2026", "WIPEDAY"]

    response = await api.post("/api/v1/messages", json=message_payload())

    assert response.status_code == 200
    assert store.codes == ["RUST2026", "WIPEDAY"]
    activations = await db_session.scalars(select(Activation).order_by(Activation.id))
    assert [(a.code, a.status) for a in activations] == [
        ("RUST2026", ActivationStatus.ACTIVATED),
        ("WIPEDAY", ActivationStatus.ACTIVATED),
    ]


async def test_nothing_is_activated_without_codes(api, extractor, store, account) -> None:
    response = await api.post("/api/v1/messages", json=message_payload(text="Вайп в пятницу"))

    assert response.status_code == 200
    assert store.codes == []
