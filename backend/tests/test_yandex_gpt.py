from app.clients.yandex_gpt import create_yandexgpt_client
from app.core.config import Settings


def make_settings(**overrides) -> Settings:
    values = {
        "db_password": "x",
        "yandex_api_key": "secret-key",
        "yandex_folder_id": "b1gtest",
        "session_encryption_key": "test",
        "admin_password": "test-password",
    }
    return Settings(**(values | overrides))


def test_model_uri_includes_folder_and_model() -> None:
    settings = make_settings(yandex_model="yandexgpt-5-pro")

    assert settings.yandex_model_uri == "gpt://b1gtest/yandexgpt-5-pro"


async def test_client_uses_yandex_settings() -> None:
    settings = make_settings(yandex_timeout=10)

    async with create_yandexgpt_client(settings) as client:
        assert client.api_key == "secret-key"
        assert client.project == "b1gtest"
        assert str(client.base_url) == "https://ai.api.cloud.yandex.net/v1/"
        assert client.timeout == 10
