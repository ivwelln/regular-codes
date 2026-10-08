import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_promo_extractor, get_session
from app.main import app
from app.models import Message, MessageStatus, PromoCode
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


@pytest.fixture
def extractor() -> FakeExtractor:
    return FakeExtractor()


@pytest.fixture
def api(client: AsyncClient, db_session: AsyncSession, extractor: FakeExtractor) -> AsyncClient:
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_promo_extractor] = lambda: extractor
    return client


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
