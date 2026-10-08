import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, MessageStatus, PromoCode
from app.schemas.message import MessageIn
from app.services.promo_extractor import PromoExtractionError, PromoExtractor

logger = logging.getLogger(__name__)


async def process_message(
    session: AsyncSession, extractor: PromoExtractor, data: MessageIn
) -> tuple[Message, list[str]]:
    message = await session.scalar(
        select(Message).where(
            Message.source == data.source,
            Message.external_id == data.external_id,
        )
    )

    if message is None:
        message = Message(source=data.source, external_id=data.external_id, text=data.text)
        session.add(message)
        await session.commit()
    elif message.status != MessageStatus.FAILED:
        return message, await _get_codes(session, message.id)

    try:
        codes = await extractor.extract(message.text)
    except PromoExtractionError as exc:
        logger.warning("Сообщение %s не проверено: %s", message.id, exc)
        message.status = MessageStatus.FAILED
        await session.commit()
        return message, []

    session.add_all(PromoCode(message_id=message.id, code=code) for code in codes)
    message.status = MessageStatus.PROCESSED
    await session.commit()
    return message, codes


async def _get_codes(session: AsyncSession, message_id: int) -> list[str]:
    result = await session.scalars(
        select(PromoCode.code).where(PromoCode.message_id == message_id).order_by(PromoCode.id)
    )
    return list(result)
