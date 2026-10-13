import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.gamestores import ActivationResult, GameStoresClient, StoreUnavailableError
from app.core.crypto import SessionCipher
from app.crud.accounts import list_accounts_to_activate
from app.crud.activations import get_activation
from app.models import Account, AccountStatus, Activation, ActivationStatus

logger = logging.getLogger(__name__)

DELAY_BETWEEN_ACCOUNTS = 2.0

STATUS_BY_RESULT = {
    ActivationResult.ACTIVATED: ActivationStatus.ACTIVATED,
    ActivationResult.NOT_FOUND: ActivationStatus.NOT_FOUND,
    ActivationResult.REJECTED: ActivationStatus.REJECTED,
}


async def activate_code(
    session: AsyncSession,
    store: GameStoresClient,
    cipher: SessionCipher,
    code: str,
    delay: float = DELAY_BETWEEN_ACCOUNTS,
) -> list[Activation]:
    activations: list[Activation] = []
    for index, account in enumerate(await list_accounts_to_activate(session, code)):
        if index > 0:
            await asyncio.sleep(delay)

        try:
            outcome = await store.use_promo_code(cipher.decrypt(account.encrypted_session), code)
        except StoreUnavailableError as exc:
            activations.append(
                await _save_activation(session, account, code, ActivationStatus.FAILED, str(exc))
            )
            continue

        if outcome.result == ActivationResult.SESSION_EXPIRED:
            logger.warning("account session %s:%s expired", account.username, account.id)
            account.status = AccountStatus.EXPIRED
            await session.commit()
            continue

        status = STATUS_BY_RESULT[outcome.result]
        activations.append(await _save_activation(session, account, code, status, outcome.message))
        if status == ActivationStatus.NOT_FOUND:
            break

    return activations


async def _save_activation(
    session: AsyncSession, account: Account, code: str, status: ActivationStatus, message: str
) -> Activation:
    activation = await get_activation(session, account.id, code)
    if activation is None:
        activation = Activation(account_id=account.id, code=code)
        session.add(activation)
    activation.status = status
    activation.message = message
    await session.commit()
    return activation
