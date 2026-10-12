import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from sqlalchemy import select

from app.api.deps import get_session, get_session_cipher, get_store
from app.clients.gamestores import Player, StoreUnavailableError
from app.core.config import get_settings
from app.core.crypto import SessionCipher
from app.main import app
from app.models import Account

ADMIN = ("admin", "test-password")


class FakeStore:
    """Отвечает вместо магазина: профиль, «сессия истекла» или недоступность."""

    def __init__(self) -> None:
        self.player: Player | None = Player(steamId="76561198000000000", username="ivan")
        self.unavailable = False
        self.calls = 0

    async def get_player(self, session: str) -> Player | None:
        self.calls += 1
        if self.unavailable:
            raise StoreUnavailableError("503")
        return self.player


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def cipher() -> SessionCipher:
    return SessionCipher(Fernet.generate_key().decode())


@pytest.fixture
def admin(client, db_session, store, cipher, test_db_settings) -> AsyncClient:
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_session_cipher] = lambda: cipher
    app.dependency_overrides[get_settings] = lambda: test_db_settings
    return client


async def test_page_requires_password(admin) -> None:
    response = await admin.get("/admin/accounts")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Basic"


async def test_page_rejects_wrong_password(admin) -> None:
    response = await admin.get("/admin/accounts", auth=("admin", "wrong"))

    assert response.status_code == 401


async def test_adding_requires_password(admin, store) -> None:
    response = await admin.post("/admin/accounts", data={"shop_session": "session-a"})

    assert response.status_code == 401
    assert store.calls == 0


async def test_adds_account_and_shows_it(admin, db_session, cipher) -> None:
    response = await admin.post(
        "/admin/accounts", data={"shop_session": "  session-a\n"}, auth=ADMIN
    )

    assert response.status_code == 303
    assert response.headers["Location"] == "/admin/accounts?saved=ivan"
    account = await db_session.scalar(select(Account))
    assert cipher.decrypt(account.encrypted_session) == "session-a"

    page = await admin.get(response.headers["Location"], auth=ADMIN)
    assert "Аккаунт ivan сохранён" in page.text
    assert "76561198000000000" in page.text
    assert "session-a" not in page.text
    assert account.encrypted_session not in page.text


@pytest.mark.parametrize(
    ("setup", "error"),
    [
        (lambda store: setattr(store, "player", None), "Магазин не принял сессию"),
        (lambda store: setattr(store, "unavailable", True), "Магазин сейчас недоступен"),
    ],
    ids=["invalid_session", "store_unavailable"],
)
async def test_shows_error_when_account_not_saved(admin, db_session, store, setup, error) -> None:
    setup(store)

    response = await admin.post("/admin/accounts", data={"shop_session": "session-a"}, auth=ADMIN)
    page = await admin.get(response.headers["Location"], auth=ADMIN)

    assert error in page.text
    assert await db_session.scalar(select(Account)) is None


async def test_escapes_username_from_store(admin, store) -> None:
    store.player = Player(steamId="1", username="<script>alert(1)</script>")

    response = await admin.post("/admin/accounts", data={"shop_session": "session-a"}, auth=ADMIN)
    page = await admin.get(response.headers["Location"], auth=ADMIN)

    assert "<script>" not in page.text
    assert "&lt;script&gt;" in page.text
