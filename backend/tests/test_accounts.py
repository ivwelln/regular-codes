import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select

from app.clients.gamestores import Player
from app.core.crypto import SessionCipher
from app.crud.accounts import list_accounts
from app.models import Account, AccountStatus
from app.services.accounts import InvalidShopSessionError, save_account


class FakeStore:
    """Возвращает заданный профиль вместо запроса к магазину."""

    def __init__(self, player: Player | None) -> None:
        self.player = player

    async def get_player(self, session: str) -> Player | None:
        return self.player


@pytest.fixture
def cipher() -> SessionCipher:
    return SessionCipher(Fernet.generate_key().decode())


def make_player(steam_id: str = "76561198000000000", username: str = "ivan") -> Player:
    return Player(steamId=steam_id, username=username)


async def count_accounts(db_session) -> int:
    return await db_session.scalar(select(func.count()).select_from(Account))


async def test_saves_new_account_with_encrypted_session(db_session, cipher) -> None:
    account = await save_account(db_session, FakeStore(make_player()), cipher, "session-a")

    assert account.steam_id == "76561198000000000"
    assert account.username == "ivan"
    assert account.status == AccountStatus.ACTIVE
    assert account.encrypted_session != "session-a"
    assert cipher.decrypt(account.encrypted_session) == "session-a"


async def test_updates_existing_account(db_session, cipher) -> None:
    account = await save_account(db_session, FakeStore(make_player()), cipher, "session-a")
    account.status = AccountStatus.EXPIRED
    await db_session.commit()

    store = FakeStore(make_player(username="ivan-new"))
    updated = await save_account(db_session, store, cipher, "session-b")

    assert updated.id == account.id
    assert updated.username == "ivan-new"
    assert updated.status == AccountStatus.ACTIVE
    assert cipher.decrypt(updated.encrypted_session) == "session-b"
    assert await count_accounts(db_session) == 1


async def test_rejects_invalid_session(db_session, cipher) -> None:
    with pytest.raises(InvalidShopSessionError):
        await save_account(db_session, FakeStore(None), cipher, "expired-session")

    assert await count_accounts(db_session) == 0


async def test_lists_accounts_in_order_of_adding(db_session, cipher) -> None:
    await save_account(db_session, FakeStore(make_player("1", "first")), cipher, "session-a")
    await save_account(db_session, FakeStore(make_player("2", "second")), cipher, "session-b")

    accounts = await list_accounts(db_session)

    assert [account.username for account in accounts] == ["first", "second"]
