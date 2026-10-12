from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.admin.routes import router as admin_router
from app.api.v1.health import router as health_router
from app.api.v1.messages import router as messages_router
from app.clients.gamestores import GameStoresClient, create_gamestores_http_client
from app.clients.yandex_gpt import create_yandexgpt_client
from app.core.config import get_settings
from app.core.crypto import SessionCipher
from app.db.session import create_engine, create_session_factory
from app.services.promo_extractor import PromoExtractor


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_engine(settings)
    app.state.session_factory = create_session_factory(engine=engine)
    try:
        async with (
            create_yandexgpt_client(settings) as yandex_gpt,
            create_gamestores_http_client(settings) as store_http,
        ):
            app.state.store = GameStoresClient(store_http)
            app.state.promo_extractor = PromoExtractor(yandex_gpt, model=settings.yandex_model_uri)
            app.state.session_cipher = SessionCipher(
                settings.session_encryption_key.get_secret_value()
            )
            yield
    finally:
        await engine.dispose()


app = FastAPI(title="Regular Codes", lifespan=lifespan)

app.include_router(health_router)
app.include_router(messages_router, prefix="/api/v1")
app.include_router(admin_router)
