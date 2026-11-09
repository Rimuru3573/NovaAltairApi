from fastapi import FastAPI
from contextlib import asynccontextmanager
import novaaltairapi.models
from novaaltairapi.db import Base, engine
from novaaltairapi.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="NovaAltairApi", lifespan=lifespan, openapi_url=None)
app.include_router(router)