import json

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.db.models import TelemetryEvent

router = APIRouter()


@router.get("/{match_id}/live-summary")
async def live_summary(
    match_id: str,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"summary_{match_id}"
    cached = await redis.get(cache_key)
    if cached is not None:
        return json.loads(cached)

    result = await db.execute(
        select(TelemetryEvent)
        .where(TelemetryEvent.match_id == match_id)
        .order_by(TelemetryEvent.timestamp.desc())
        .limit(10)
    )
    events = result.scalars().all()
    if not events:
        raise HTTPException(status_code=404, detail="Match not found")

    prediction_raw = await redis.get(f"match_prediction_{match_id}")
    prediction = json.loads(prediction_raw) if prediction_raw else None

    response = {
        "match_id": match_id,
        "recent_events": [
            {
                "id": str(e.id),
                "player_id": e.player_id,
                "event_type": e.event_type,
                "x": e.coord_x,
                "y": e.coord_y,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ],
        "prediction": prediction,
    }

    response_json = json.dumps(response, default=str)
    await redis.setex(cache_key, 3, response_json)

    return response
