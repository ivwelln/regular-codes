import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

_secrets_dir = Path(os.getenv("APP_SECRETS_DIR", "/run/secrets"))
SECRETS_DIR = _secrets_dir if _secrets_dir.is_dir() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        secrets_dir=SECRETS_DIR,
        frozen=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    debug: bool = False

    db_password: SecretStr
    db_user: str = "app"
    db_name: str = "app"
    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_pool_size: int = Field(default=5, ge=1)
    db_pool_timeout: int = Field(default=30, ge=0)
    db_pool_pre_ping: bool = True
    db_max_overflow: int = Field(default=5, ge=0)
    db_echo: bool = False

    yandex_api_key: SecretStr = Field(min_length=1)
    yandex_folder_id: str = Field(min_length=1)
    yandex_model: str = "yandexgpt-5-lite"
    yandex_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    yandex_timeout: float = Field(default=30, gt=0)

    gamestores_base_url: str = "https://syndicate.gamestores.app/api/v1"
    gamestores_timeout: float = Field(default=15, gt=0)

    session_encryption_key: SecretStr = Field(min_length=1)

    admin_username: str = "admin"
    admin_password: SecretStr = Field(min_length=1)

    @property
    def db_url(self) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=self.db_user,
            host=self.db_host,
            database=self.db_name,
            password=self.db_password.get_secret_value(),
            port=self.db_port,
        )

    @property
    def yandex_model_uri(self) -> str:
        return f"gpt://{self.yandex_folder_id}/{self.yandex_model}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
