from openai import AsyncOpenAI

from app.core.config import Settings


def create_yandexgpt_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.yandex_api_key.get_secret_value(),
        base_url=settings.yandex_base_url,
        project=settings.yandex_folder_id,
        timeout=settings.yandex_timeout,
        max_retries=settings.yandex_max_retries,
    )
