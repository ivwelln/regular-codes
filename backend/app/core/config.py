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


@lru_cache
def get_settings() -> Settings:
    return Settings()
