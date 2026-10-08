from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.promo_extractor import PromoExtractor


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_promo_extractor(request: Request) -> PromoExtractor:
    return request.app.state.promo_extractor


SessionDep = Annotated[AsyncSession, Depends(get_session)]
PromoExtractorDep = Annotated[PromoExtractor, Depends(get_promo_extractor)]
