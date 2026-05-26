from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.schemas.telemetry import TelemetryEventInput
from app.core.redis import get_redis

router = APIRouter()


@router.post("/telemetry", status_code=202)
async def ingest_telemetry(
    event: TelemetryEventInput,
    redis: Redis = Depends(get_redis),
):
    event_json = event.model_dump_json()
    await redis.lpush("telemetry_buffer", event_json)
    return {"status": "queued"}
