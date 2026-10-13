import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.clients.gamestores import ActivationOutcome, ActivationResult, StoreUnavailableError
from app.core.crypto import SessionCipher
from app.models import Account, AccountStatus, Activation, ActivationStatus
from app.services.activation import activate_code


class FakeStore:
    """Отвечает на активацию по сессии аккаунта и запоминает, какие сессии пробовали."""

    def __init__(self) -> None:
        self.outcomes: dict[str, ActivationOutcome | Exception] = {}
        self.calls: list[str] = []

    async def use_promo_code(self, session: str, code: str) -> ActivationOutcome:
        self.calls.append(session)
        outcome = self.outcomes.get(session, ActivationOutcome(ActivationResult.ACTIVATED, "ok"))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def cipher() -> SessionCipher:
    return SessionCipher(Fernet.generate_key().decode())


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def add_account(db_session, cipher):
    async def add(name: str, status: AccountStatus = AccountStatus.ACTIVE) -> Account:
        account = Account(
            steam_id=f"id-{name}",
            username=name,
            encrypted_session=cipher.encrypt(f"session-{name}"),
            status=status,
        )
        db_session.add(account)
        await db_session.commit()
        return account

    return add


async def activations_by_user(db_session) -> dict[str, tuple[ActivationStatus, str]]:
    rows = await db_session.execute(
        select(Account.username, Activation.status, Activation.message).join(
            Activation, Activation.account_id == Account.id
        )
    )
    return {username: (status, message) for username, status, message in rows}


async def activate(db_session, store, cipher, code: str = "RUST2026"):
    return await activate_code(db_session, store, cipher, code, delay=0)


async def test_activates_code_on_active_accounts(db_session, store, cipher, add_account) -> None:
    await add_account("ivan")
    await add_account("petr")
    await add_account("old", status=AccountStatus.EXPIRED)
    store.outcomes["session-petr"] = ActivationOutcome(ActivationResult.REJECTED, "Уже использован")

    await activate(db_session, store, cipher)

    assert store.calls == ["session-ivan", "session-petr"]
    assert await activations_by_user(db_session) == {
        "ivan": (ActivationStatus.ACTIVATED, "ok"),
        "petr": (ActivationStatus.REJECTED, "Уже использован"),
    }


async def test_does_not_try_same_code_twice(db_session, store, cipher, add_account) -> None:
    await add_account("ivan")
    await activate(db_session, store, cipher)

    await activate(db_session, store, cipher)

    assert store.calls == ["session-ivan"]


async def test_new_code_is_tried_again(db_session, store, cipher, add_account) -> None:
    await add_account("ivan")
    await activate(db_session, store, cipher, code="RUST2026")

    await activate(db_session, store, cipher, code="WIPEDAY")

    assert store.calls == ["session-ivan", "session-ivan"]


async def test_failed_attempt_is_retried(db_session, store, cipher, add_account) -> None:
    await add_account("ivan")
    store.outcomes["session-ivan"] = StoreUnavailableError("503")
    await activate(db_session, store, cipher)
    assert await activations_by_user(db_session) == {"ivan": (ActivationStatus.FAILED, "503")}

    store.outcomes.clear()
    await activate(db_session, store, cipher)

    assert await activations_by_user(db_session) == {"ivan": (ActivationStatus.ACTIVATED, "ok")}


async def test_expired_session_marks_account(db_session, store, cipher, add_account) -> None:
    account = await add_account("ivan")
    store.outcomes["session-ivan"] = ActivationOutcome(
        ActivationResult.SESSION_EXPIRED, "Необходима авторизация"
    )

    await activate(db_session, store, cipher)

    assert account.status == AccountStatus.EXPIRED
    assert await activations_by_user(db_session) == {}


async def test_stops_when_code_not_found(db_session, store, cipher, add_account) -> None:
    await add_account("ivan")
    await add_account("petr")
    store.outcomes["session-ivan"] = ActivationOutcome(
        ActivationResult.NOT_FOUND, "Промокод не найден"
    )

    await activate(db_session, store, cipher)

    assert store.calls == ["session-ivan"]
    assert await activations_by_user(db_session) == {
        "ivan": (ActivationStatus.NOT_FOUND, "Промокод не найден")
    }
