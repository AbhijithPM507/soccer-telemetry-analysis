# Master Blueprint: High-Throughput Soccer Match Analytics Engine

## 🤖 Agent Execution Protocol (CRITICAL)
You are acting as a Senior Backend Engineer. I am the Lead Systems Architect. 
1. **Zero-Shot Ban:** Do NOT generate the entire project in one response. This will overwhelm the context window and lead to cascading errors.
2. **Strict Phasing:** You must execute this blueprint exactly one phase at a time.
3. **The Checkpoint Rule:** At the end of every phase, you must STOP generating code. You will output a summary of what was built, report any dependency issues, and explicitly ask: *"Ready for Phase [X]?"* Do not proceed until I give the command.
4. **Architectural Integrity:** Adhere strictly to the Allowed/Banned tech stacks and the exact file structures defined below.

---

## Phase 1: Environment Scaffolding & Dependencies
**Objective:** Establish a clean, modular Python workspace and install exact dependencies.

* **Tech Stack Allowed:** Python 3.10+, `venv`, `pip`, Git.
* **Tech Stack Banned:** Dockerfiles (not yet), globally installed packages.
* **Directory Structure to Create:**
  * `app/` (Main application root)
    * `api/` (Endpoints and routers)
    * `core/` (Config and DB connections)
    * `db/` (SQLAlchemy models and migrations)
    * `schemas/` (Pydantic validation models)
    * `ml/` (AI/ML inference logic)
    * `workers/` (Background task logic)
  * `scripts/` (Simulator and utility scripts)
  * `.gitignore`
* **Dependencies (`requirements.txt`) to define:**
  * `fastapi`, `uvicorn[standard]`
  * `sqlalchemy`, `asyncpg` (for async Postgres)
  * `alembic` (for migrations)
  * `redis`, `pydantic`, `pydantic-settings`
  * `celery` (for robust background workers)

> **Checkpoint:** Agent must stop, confirm folders are created, and wait for approval.

---

## Phase 2: Local Infrastructure (Dockerized Data Layer)
**Objective:** Spin up the exact database and cache environment using Docker Compose.

* **Tech Stack Allowed:** Docker Compose, PostgreSQL 15 (Alpine), Redis 7 (Alpine).
* **Tech Stack Banned:** Local host installations of Postgres/Redis, SQLite, MongoDB.
* **Files to Create:**
  * `docker-compose.yml`:
    * **Service 1:** `postgres`. Image: `postgres:15-alpine`. Ports: `5432:5432`. Volume: `pg_data:/var/lib/postgresql/data`.
    * **Service 2:** `redis`. Image: `redis:7-alpine`. Ports: `6379:6379`.
  * `.env` (and `.env.example`):
    * Define `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
    * Define `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db_name`.
    * Define `REDIS_URL=redis://localhost:6379/0`.

> **Checkpoint:** Agent must output the compose file and `.env` template, then wait.

---

## Phase 3: Data Blueprints & Schemas
**Objective:** Define the strict data shapes for validation (Pydantic) and storage (SQLAlchemy).

* **Tech Stack Allowed:** SQLAlchemy 2.0 (Declarative Base), Pydantic V2, Alembic.
* **Files to Create:**
  * `app/schemas/telemetry.py`: 
    * Create `TelemetryEventInput`: `match_id` (str), `timestamp` (datetime), `event_type` (str), `player_id` (str), `x` (float), `y` (float).
  * `app/db/models.py`:
    * Table `matches`: `id` (PK, str), `status` (str), `home_team` (str), `away_team` (str).
    * Table `telemetry_events`: `id` (PK, UUID), `match_id` (FK to matches, index=True), `player_id` (str), `event_type` (str, index=True), `coord_x` (float), `coord_y` (float), `timestamp` (datetime, index=True).
  * `app/core/database.py`: Define the async SQLAlchemy engine and session maker.
* **Actions:** Initialize Alembic (`alembic init alembic`), configure `env.py` for async models, and generate the first migration.

> **Checkpoint:** Agent must present the schemas, models, and Alembic setup, then wait.

---

## Phase 4: The ML Inference Stub
**Objective:** Isolate the AI logic into a standalone module that can be swapped later without breaking the API.

* **Tech Stack Allowed:** Python standard library.
* **Tech Stack Banned:** PyTorch, Scikit-Learn, Pandas (keep it lightweight for the initial build).
* **Files to Create:**
  * `app/ml/model.py`:
    * Create class `MatchPredictor`.
    * Create async method `predict_goal_probability(match_state: list[dict]) -> dict`.
    * **Logic:** For now, calculate a fake "threat score" by checking if `coord_x` is near the goal area (e.g., `x > 80`). Return a dictionary: `{"home_prob": random_float, "away_prob": random_float, "momentum": string}`.

> **Checkpoint:** Agent must present the ML stub class, then wait.

---

## Phase 5: The High-Speed Ingestion API (The Buffer)
**Objective:** Build the endpoint that receives firehose data and buffers it into Redis.

* **Tech Stack Allowed:** FastAPI, `redis.asyncio`.
* **Tech Stack Banned:** SQLAlchemy/Postgres imports in this file. (Do NOT write to DB here).
* **Files to Create:**
  * `app/core/redis.py`: Setup async Redis connection pool.
  * `app/api/routers/ingest.py`:
    * Route: `@router.post("/telemetry", status_code=202)`.
    * Logic: Accept `TelemetryEventInput`. Serialize to JSON string. Execute `await redis.lpush("telemetry_buffer", event_json)`. Return `{"status": "queued"}`.
  * `app/main.py`: Initialize FastAPI app, include routers, add startup/shutdown events for DB and Redis connections.

> **Checkpoint:** Agent must present the FastAPI routing and Redis push logic, then wait.

---

## Phase 6: The Micro-Batching Background Worker
**Objective:** Safely drain the Redis queue and perform bulk writes to PostgreSQL.

* **Tech Stack Allowed:** Celery OR `asyncio.create_task` background loops, SQLAlchemy `insert().values()`.
* **Files to Create:**
  * `app/workers/batch_processor.py`:
    * Create a continuous background loop (runs every 2.0 seconds).
    * **Logic:** 1. Execute `redis.rpop("telemetry_buffer", count=1000)` to pull a batch.
      2. If batch is empty, sleep and continue.
      3. If batch has data, parse JSON strings back into Python dicts.
      4. Pass the batch to `MatchPredictor.predict_goal_probability()`. (Store the prediction in Redis as `match_prediction_{match_id}`).
      5. Map dicts to the SQLAlchemy `telemetry_events` table.
      6. Execute a single bulk insert using `session.execute(insert(TelemetryEvent).values(batch_data))`. Commit the transaction.

> **Checkpoint:** Agent must present the batch-processing logic and bulk insert syntax, then wait.

---

## Phase 7: The Client-Facing Read API
**Objective:** Serve live match states using the Cache-Aside pattern.

* **Tech Stack Allowed:** FastAPI, Redis, SQLAlchemy.
* **Tech Stack Banned:** N+1 queries.
* **Files to Create:**
  * `app/api/routers/matches.py`:
    * Route: `@router.get("/{match_id}/live-summary")`.
    * **Logic:**
      1. Check Redis for key `summary_{match_id}`. If it exists, return it instantly (Cache Hit).
      2. Cache Miss: Query Postgres for the last 10 events for `match_id`. Fetch the latest ML prediction from Redis `match_prediction_{match_id}`.
      3. Construct a combined JSON response.
      4. Execute `await redis.setex("summary_{match_id}", 3, response_json)` to cache it for 3 seconds.
      5. Return response.

> **Checkpoint:** Agent must present the Read API and cache-aside implementation, then wait.

---

## Phase 8: The Stress-Test Simulator
**Objective:** Artificially bombard the ingestion API to verify the micro-batching architecture.

* **Tech Stack Allowed:** `asyncio`, `aiohttp`.
* **Tech Stack Banned:** Synchronous `requests` library.
* **Files to Create:**
  * `scripts/simulate.py`:
    * Setup `aiohttp.ClientSession`.
    * Create a loop that generates randomized `TelemetryEventInput` payloads.
    * Use `asyncio.gather` to fire 50 to 100 concurrent POST requests per second to `http://localhost:8000/telemetry`.
    * Track and print successful `202 Accepted` responses versus failed requests.

> **Final Checkpoint:** Agent presents the simulator script, concluding the blueprint.