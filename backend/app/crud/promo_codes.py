from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromoCode


async def list_message_codes(session: AsyncSession, message_id: int) -> list[str]:
    result = await session.scalars(
        select(PromoCode.code).where(PromoCode.message_id == message_id).order_by(PromoCode.id)
    )
    return list(result)
