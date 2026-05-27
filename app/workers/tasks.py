import asyncio
import json
import logging
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.models import Match, TelemetryEvent
from app.ml.model import MatchPredictor

logger = logging.getLogger(__name__)

predictor = MatchPredictor()


async def _process_batch():
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
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

        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            for mid in match_ids:
                await session.execute(
                    pg_insert(Match)
                    .values(id=mid, status="live", home_team="Home", away_team="Away")
                    .on_conflict_do_nothing()
                )
            await session.execute(insert(TelemetryEvent).values(batch_data))
            await session.commit()

        await engine.dispose()
        return len(events)
    finally:
        await redis.close()


@celery_app.task
def process_batch_task():
    result = asyncio.run(_process_batch())
    if result:
        logger.info("Batch processed %d events", result)
    return result
