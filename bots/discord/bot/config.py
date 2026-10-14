import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_secrets_dir = Path(os.getenv("BOT_SECRETS_DIR", "/run/secrets"))
SECRETS_DIR = _secrets_dir if _secrets_dir.is_dir() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BOT_",
        secrets_dir=SECRETS_DIR,
        frozen=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    discord_token: SecretStr = Field(min_length=1)
    channel_ids: frozenset[int] = Field(min_length=1)
    backend_url: str = "http://backend:8000/api/v1"
    backend_timeout: float = Field(default=30, gt=0)

    history_days: int = Field(default=7, ge=0)
