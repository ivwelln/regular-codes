from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account


async def get_account_by_steamid(session: AsyncSession, steam_id: str) -> Account | None:
    return await session.scalar(select(Account).where(Account.steam_id == steam_id))


async def list_accounts(session: AsyncSession) -> list[Account]:
    result = await session.scalars(select(Account).order_by(Account.id))
    return list(result)
