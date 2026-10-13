import secrets
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.clients.gamestores import GameStoresClient
from app.core.config import Settings, get_settings
from app.core.crypto import SessionCipher
from app.services.promo_extractor import PromoExtractor

basic_auth = HTTPBasic()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


async def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


def get_promo_extractor(request: Request) -> PromoExtractor:
    return request.app.state.promo_extractor


def get_store(request: Request) -> GameStoresClient:
    return request.app.state.store


def get_session_cipher(request: Request) -> SessionCipher:
    return request.app.state.session_cipher


def require_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(basic_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    username_ok = secrets.compare_digest(
        credentials.username.encode(), settings.admin_username.encode()
    )
    password_ok = secrets.compare_digest(
        credentials.password.encode(), settings.admin_password.get_secret_value().encode()
    )
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionFactoryDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]
PromoExtractorDep = Annotated[PromoExtractor, Depends(get_promo_extractor)]
StoreDep = Annotated[GameStoresClient, Depends(get_store)]
SessionCipherDep = Annotated[SessionCipher, Depends(get_session_cipher)]
