from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activation


async def get_activation(session: AsyncSession, account_id: int, code: str) -> Activation | None:
    return await session.scalar(
        select(Activation).where(Activation.account_id == account_id, Activation.code == code)
    )
