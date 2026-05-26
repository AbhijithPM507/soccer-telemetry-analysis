import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.redis import get_redis
from app.db.models import Match, TelemetryEvent
from app.ml.model import MatchPredictor

logger = logging.getLogger(__name__)

predictor = MatchPredictor()


async def process_batch() -> int:
    redis = await get_redis()
    raw_events = await redis.rpop("telemetry_buffer", count=1000)
    if not raw_events:
        return 0

    events = []
    match_ids = set()
    for raw in raw_events:
        try:
            event = json.loads(raw)
            events.append(event)
            match_ids.add(event["match_id"])
        except (json.JSONDecodeError, KeyError):
            continue

    for match_id in match_ids:
        match_events = [e for e in events if e["match_id"] == match_id]
        prediction = await predictor.predict_goal_probability(match_events)
        await redis.setex(
            f"match_prediction_{match_id}", 30,
            json.dumps(prediction),
        )

    batch_data = [
        {
            "match_id": e["match_id"],
            "player_id": e["player_id"],
            "event_type": e["event_type"],
            "coord_x": e["x"],
            "coord_y": e["y"],
            "timestamp": datetime.fromisoformat(
                e["timestamp"].replace("Z", "+00:00")
            ).replace(tzinfo=None),
        }
        for e in events
    ]

    async with async_session() as session:
        for mid in match_ids:
            await session.execute(
                pg_insert(Match)
                .values(id=mid, status="live", home_team="Home", away_team="Away")
                .on_conflict_do_nothing()
            )
        await session.execute(insert(TelemetryEvent).values(batch_data))
        await session.commit()

    return len(events)


async def batch_loop():
    while True:
        try:
            count = await process_batch()
            if count:
                logger.info("Batch processed %d events", count)
        except Exception:
            logger.exception("Batch processing error")
        await asyncio.sleep(2.0)
