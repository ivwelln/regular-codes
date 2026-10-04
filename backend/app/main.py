from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.db.session import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await engine.dispose()
    
app = FastAPI(title="Regular Codes", lifespan=lifespan)

app.include_router(health_router)