import httpx2

from bot.config import Settings

SOURCE = "discord"
MAX_TEXT_LENGTH = 4000


def create_backend_http_client(settings: Settings) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(base_url=settings.backend_url, timeout=settings.backend_timeout)


class BackendClient:
    def __init__(self, http: httpx2.AsyncClient) -> None:
        self._http = http

    async def send_message(self, external_id: str, text: str) -> list[str]:
        response = await self._http.post(
            "/messages",
            json={"source": SOURCE, "external_id": external_id, "text": text[:MAX_TEXT_LENGTH]},
        )
        response.raise_for_status()
        return response.json()["codes"]
