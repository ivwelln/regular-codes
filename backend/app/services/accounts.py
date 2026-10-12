from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.gamestores import GameStoresClient
from app.core.crypto import SessionCipher
from app.crud.accounts import get_account_by_steamid
from app.models.account import Account, AccountStatus


class InvalidShopSessionError(Exception):
    """Store denied session: wrong or expired session."""


async def save_account(
    session: AsyncSession, store: GameStoresClient, cipher: SessionCipher, shop_session: str
) -> Account:
    player = await store.get_player(shop_session)
    if player is None:
        raise InvalidShopSessionError

    account = await get_account_by_steamid(session, player.steam_id)
    if account is None:
        account = Account(steam_id=player.steam_id)
        session.add(account)

    account.username = player.username
    account.encrypted_session = cipher.encrypt(shop_session)
    account.status = AccountStatus.ACTIVE

    await session.commit()
    return account
