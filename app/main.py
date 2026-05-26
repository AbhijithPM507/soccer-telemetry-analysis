import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from app.core.database import engine
from app.core.redis import close_redis, get_redis
from app.api.routers import ingest, matches
from app.workers.batch_processor import batch_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        pass
    await get_redis()
    task = asyncio.create_task(batch_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await close_redis()
    await engine.dispose()


app = FastAPI(title="Soccer Telemetry", lifespan=lifespan)

app.include_router(ingest.router, prefix="/api", tags=["ingest"])
app.include_router(matches.router, prefix="/api/matches", tags=["matches"])
