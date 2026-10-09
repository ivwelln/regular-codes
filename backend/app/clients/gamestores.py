import enum
from dataclasses import dataclass
from typing import Any

import httpx2
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings

PROMO_CODE_NOT_FOUND = "Промокод не найден"


class ActivationResult(enum.StrEnum):
    ACTIVATED = "activated"
    NOT_FOUND = "not_found"
    REJECTED = "rejected"
    SESSION_EXPIRED = "session_expired"


@dataclass(frozen=True)
class ActivationOutcome:
    result: ActivationResult
    message: str


class Player(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    steam_id: str = Field(alias="steamId")
    username: str


class StoreUnavailableError(Exception):
    """Магазин временно недоступен. Нужно повторить попытку позже."""


def create_gamestores_http_client(settings: Settings) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        base_url=settings.gamestores_base_url,
        headers={"Accept": "application/json"},
        timeout=settings.gamestores_timeout,
    )


class GameStoresClient:
    def __init__(self, http: httpx2.AsyncClient) -> None:
        self._http = http

    async def get_player(self, session: str) -> Player | None:
        data = await self._request("GET", "/player.info", session)
        if data.get("logged") is False:
            return None
        if data.get("result") != "success":
            raise StoreUnavailableError(f"Не удалось получить профиль: {data.get('message')}")
        return Player.model_validate(data["data"])

    async def use_promo_code(self, session: str, code: str) -> ActivationOutcome:
        data = await self._request("POST", "/player.usePromoCode", session, {"promocode": code})
        if data.get("result") == "success":
            return ActivationOutcome(
                ActivationResult.ACTIVATED, " ".join(data.get("messages") or [])
            )
        message = str(data.get("message", ""))
        if data.get("logged") is False:
            return ActivationOutcome(ActivationResult.SESSION_EXPIRED, message)
        if message == PROMO_CODE_NOT_FOUND:
            return ActivationOutcome(ActivationResult.NOT_FOUND, message)
        return ActivationOutcome(ActivationResult.REJECTED, message)

    async def _request(
        self, method: str, path: str, session: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            response = await self._http.request(
                method, path, json=payload, headers={"Cookie": f"SessionShop={session}"}
            )
            response.raise_for_status()
            data = response.json()
        except httpx2.HTTPError as exc:
            raise StoreUnavailableError(f"Ошибка запроса к магазину: {exc!r}") from exc
        except ValueError as exc:
            raise StoreUnavailableError(
                "Магазин вернул не json. Возможно, защита от ботов"
            ) from exc

        if not isinstance(data, dict):
            raise StoreUnavailableError("Магазин ответил неожиданным форматом")
        if data.get("maintenance") or data.get("storeBanned"):
            raise StoreUnavailableError("Магазин на обслуживании или заблокирован")
        return data
