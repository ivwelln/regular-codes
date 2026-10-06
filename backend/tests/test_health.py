from httpx import AsyncClient

from app.api.deps import get_session
from app.main import app


class FakeSession:
    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement) -> None:
        self.statements.append(str(statement))


async def test_health_returns_ok(client: AsyncClient) -> None:
    session = FakeSession()

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert session.statements == ["SELECT 1"]
