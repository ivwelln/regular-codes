from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message


async def get_message(session: AsyncSession, source: str, external_id: str) -> Message | None:
    return await session.scalar(
        select(Message).where(Message.source == source, Message.external_id == external_id)
    )
