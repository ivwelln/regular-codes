from fastapi import APIRouter

from app.api.deps import PromoExtractorDep, SessionDep
from app.schemas.message import MessageIn, MessageOut
from app.services.messages import process_message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("")
async def create_message(
    data: MessageIn, session: SessionDep, extractor: PromoExtractorDep
) -> MessageOut:
    message, codes = await process_message(session, extractor, data)
    return MessageOut(id=message.id, status=message.status, codes=codes)
