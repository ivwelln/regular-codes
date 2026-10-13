import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.main import app
from app.models import Base

TEST_DB_NAME = "app_test"
DB_PASSWORD_FILE = Path(__file__).parents[2] / "secrets" / "app_db_password"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _recreate_test_database(settings: Settings) -> None:
    admin_engine = create_async_engine(
        settings.db_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    await admin_engine.dispose()

    engine = create_async_engine(settings.db_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture(scope="session")
def test_db_settings() -> Settings:
    settings = Settings(
        db_password=DB_PASSWORD_FILE.read_text().strip(),
        db_host=os.getenv("TEST_DB_HOST", "localhost"),
        db_port=int(os.getenv("TEST_DB_PORT", "5432")),
        db_name=TEST_DB_NAME,
        yandex_api_key="test",
        yandex_folder_id="test",
        session_encryption_key="test",
        admin_password="test-password",
    )
    asyncio.run(_recreate_test_database(settings))
    return settings


@pytest.fixture
async def db_connection(test_db_settings: Settings) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(test_db_settings.db_url, poolclass=NullPool)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            yield conn
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
def db_session_factory(db_connection: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=db_connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with db_session_factory() as session:
        yield session
