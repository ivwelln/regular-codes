import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.messages import get_message
from app.crud.promo_codes import list_message_codes
from app.models import Message, MessageStatus, PromoCode
from app.schemas.message import MessageIn
from app.services.promo_extractor import PromoExtractionError, PromoExtractor

logger = logging.getLogger(__name__)


async def process_message(
    session: AsyncSession, extractor: PromoExtractor, data: MessageIn
) -> tuple[Message, list[str]]:
    message = await get_message(session, data.source, data.external_id)

    if message is None:
        message = Message(source=data.source, external_id=data.external_id, text=data.text)
        session.add(message)
        await session.commit()
    elif message.status != MessageStatus.FAILED:
        return message, await list_message_codes(session, message.id)

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
