from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(settings=get_settings())
    app.state.session_factory = create_session_factory(engine=engine)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Regular Codes", lifespan=lifespan)

app.include_router(health_router)
