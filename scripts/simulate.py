import asyncio
import json
import random
import sys
import time
from datetime import datetime, UTC

import aiohttp

MATCH_IDS = [f"match_{i}" for i in range(5)]
PLAYER_IDS = [f"player_{i}" for i in range(22)]
EVENT_TYPES = ["pass", "shot", "tackle", "dribble", "save"]


def generate_event():
    return {
        "match_id": random.choice(MATCH_IDS),
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": random.choice(EVENT_TYPES),
        "player_id": random.choice(PLAYER_IDS),
        "x": round(random.uniform(0, 105), 2),
        "y": round(random.uniform(0, 68), 2),
    }


async def send_request(session: aiohttp.ClientSession) -> bool:
    payload = generate_event()
    try:
        async with session.post(
            "http://localhost:8000/api/telemetry",
            json=payload,
        ) as resp:
            return resp.status == 202
    except Exception:
        return False


async def run_batch(session: aiohttp.ClientSession, concurrency: int) -> tuple[int, int]:
    results = await asyncio.gather(
        *[send_request(session) for _ in range(concurrency)]
    )
    success = sum(results)
    failed = concurrency - success
    return success, failed


async def main(duration: int = 15, concurrency: int = 100):
    print(f"Simulator starting: {concurrency} req/s for {duration}s")
    print(f"Target: http://localhost:8000/api/telemetry")
    print("-" * 50)

    async with aiohttp.ClientSession() as session:
        start = time.monotonic()
        total_success = 0
        total_failed = 0
        rounds = 0

        while time.monotonic() - start < duration:
            success, failed = await run_batch(session, concurrency)
            total_success += success
            total_failed += failed
            rounds += 1
            elapsed = time.monotonic() - start
            rate = (success + failed) / (elapsed / rounds) if rounds > 0 else 0
            print(
                f"[{elapsed:5.1f}s] "
                f"OK={success:4d}  FAIL={failed:3d}  "
                f"rate={rate:.0f} req/s"
            )
            await asyncio.sleep(1.0)

    elapsed = time.monotonic() - start
    print("-" * 50)
    print(f"Done in {elapsed:.1f}s")
    print(f"Total OK:   {total_success}")
    print(f"Total FAIL: {total_failed}")
    print(f"Throughput: {total_success / elapsed:.0f} req/s")

    return total_failed == 0


if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    success = asyncio.run(main(duration, concurrency))
    sys.exit(0 if success else 1)
