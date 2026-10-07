import json

import httpx2
import pytest
from openai import AsyncOpenAI

from app.services.promo_extractor import SYSTEM_PROMPT, PromoExtractionError, PromoExtractor

MODEL = "gpt://b1gtest/yandexgpt-5-lite"


def chat_completion(
    content: str | None, finish_reason: str = "stop", refusal: str | None = None
) -> dict:
    return {
        "id": "test",
        "object": "chat.completion",
        "created": 0,
        "model": MODEL,
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content, "refusal": refusal},
            }
        ],
    }


class FakeYandex:
    """Отвечает вместо Яндекса и запоминает присланные запросы."""

    def __init__(self) -> None:
        self.response = httpx2.Response(200, json=chat_completion('{"codes": []}'))
        self.requests: list[dict] = []

    def reply(self, codes: list[str]) -> None:
        content = json.dumps({"codes": codes})
        self.response = httpx2.Response(200, json=chat_completion(content))

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(json.loads(request.content))
        return self.response


@pytest.fixture
def yandex() -> FakeYandex:
    return FakeYandex()


@pytest.fixture
async def extractor(yandex: FakeYandex):
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(yandex.handle))
    async with AsyncOpenAI(
        api_key="test",
        base_url="https://llm.test/v1",
        http_client=http,
        max_retries=0,
    ) as client:
        yield PromoExtractor(client, model=MODEL)


async def test_returns_codes_found_by_model(extractor, yandex) -> None:
    yandex.reply(["RUST2026"])

    codes = await extractor.extract("Заходите на сервер! Промокод RUST2026 даёт кит.")

    assert codes == ["RUST2026"]


async def test_sends_prompt_and_message_to_model(extractor, yandex) -> None:
    await extractor.extract("Промокод RUST2026")

    request = yandex.requests[0]
    assert request["model"] == MODEL
    assert request["temperature"] == 0
    assert request["messages"] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Промокод RUST2026"},
    ]
    assert request["response_format"]["type"] == "json_schema"


async def test_returns_empty_list_when_no_codes(extractor, yandex) -> None:
    yandex.reply([])

    assert await extractor.extract("Вайп в пятницу в 18:00") == []


async def test_drops_codes_missing_from_message(extractor, yandex) -> None:
    yandex.reply(["RUST2026", "INVENTED"])

    assert await extractor.extract("Промокод RUST2026") == ["RUST2026"]


async def test_drops_codes_that_are_part_of_a_word(extractor, yandex) -> None:
    yandex.reply(["RUST"])

    assert await extractor.extract("Промокод RUST2026") == []


async def test_returns_code_as_written_in_message(extractor, yandex) -> None:
    yandex.reply(["RUST2026"])

    assert await extractor.extract("промокод rust2026") == ["rust2026"]


async def test_cleans_and_deduplicates_codes(extractor, yandex) -> None:
    yandex.reply([" RUST2026 ", "RUST2026", "", "two words"])

    assert await extractor.extract("RUST2026! Ещё раз: RUST2026, two words") == ["RUST2026"]


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(200, json=chat_completion('{"codes": ["RUST', finish_reason="length")),
        httpx2.Response(200, json=chat_completion("", finish_reason="content_filter")),
        httpx2.Response(200, json=chat_completion("not json")),
        httpx2.Response(200, json=chat_completion(None, refusal="Не могу ответить")),
    ],
    ids=["truncated", "content_filter", "invalid_json", "refusal"],
)
async def test_returns_empty_list_when_model_cannot_parse_message(
    extractor, yandex, response, caplog
) -> None:
    yandex.response = response

    assert await extractor.extract("Промокод RUST2026") == []
    assert "Нейросеть" in caplog.text


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(500, json={"error": {"message": "Internal error"}}),
        httpx2.Response(429, json={"error": {"message": "Too many requests"}}),
        httpx2.Response(401, json={"error": {"message": "Unknown api key"}}),
    ],
    ids=["server_error", "rate_limit", "unauthorized"],
)
async def test_raises_when_yandex_unavailable(extractor, yandex, response) -> None:
    yandex.response = response

    with pytest.raises(PromoExtractionError):
        await extractor.extract("Промокод RUST2026")
