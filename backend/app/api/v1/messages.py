from fastapi import APIRouter, BackgroundTasks

from app.api.deps import (
    PromoExtractorDep,
    SessionCipherDep,
    SessionDep,
    SessionFactoryDep,
    StoreDep,
)
from app.schemas.message import MessageIn, MessageOut
from app.services.activation import activate_codes
from app.services.messages import process_message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("")
async def create_message(
    data: MessageIn,
    session: SessionDep,
    extractor: PromoExtractorDep,
    background_tasks: BackgroundTasks,
    session_factory: SessionFactoryDep,
    store: StoreDep,
    cipher: SessionCipherDep,
) -> MessageOut:
    message, codes = await process_message(session, extractor, data)
    if codes:
        background_tasks.add_task(activate_codes, session_factory, store, cipher, codes)
    return MessageOut(id=message.id, status=message.status, codes=codes)
