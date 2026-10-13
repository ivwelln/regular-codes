from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, AccountStatus, Activation, ActivationStatus


async def get_account_by_steamid(session: AsyncSession, steam_id: str) -> Account | None:
    return await session.scalar(select(Account).where(Account.steam_id == steam_id))


async def list_accounts(session: AsyncSession) -> list[Account]:
    result = await session.scalars(select(Account).order_by(Account.id))
    return list(result)


async def list_accounts_to_activate(session: AsyncSession, code: str) -> list[Account]:
    already_tried = select(Activation.account_id).where(
        Activation.code == code, Activation.status != ActivationStatus.FAILED
    )
    result = await session.scalars(
        select(Account)
        .where(Account.status == AccountStatus.ACTIVE, Account.id.not_in(already_tried))
        .order_by(Account.id)
    )
    return list(result)
