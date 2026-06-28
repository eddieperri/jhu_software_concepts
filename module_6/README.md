## Module 6

This README explains how to build, run, and verify the Grad Cafe Analytics stack (Flask web, RabbitMQ, background worker, Postgres) using Docker Compose.

Prerequisites
- Docker and Docker Compose available on your machine (Compose v2 or later recommended).
- Optional: Python 3.11 if you want to run services locally without containers.

Key files
- `docker-compose.yml`: Compose orchestration for `db`, `rabbitmq`, `web`, and `worker`.
- `src/web/Dockerfile` and `src/worker/Dockerfile`: service images.
- `src/web/run.py`: Flask app entrypoint and routes.
- `src/worker/consumer.py`: RabbitMQ consumer and task handlers.

Ports and Endpoints
- `8080` → Flask UI (analysis dashboard). Click **Pull Data** to queue a `scrape_new_data` task and **Update Analysis** to queue `recompute_analytics`.
- `15672` → RabbitMQ management UI (guest/guest).
- `5432` → PostgreSQL (mapped for local debugging).

Environment variables (used in Compose)
- `RABBITMQ_URL` — AMQP URL used by `web` and `worker` (default: `amqp://guest:guest@rabbitmq:5672/`).
- `DATABASE_URL` — Postgres connection used by services (default: `postgresql://postgres:postgres@db:5432/postgres`).
- `PYTHONUNBUFFERED=1` — ensures Python logs are flushed immediately.
- For local non-container runs prefer using a `.env` file with `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

Build and run (Docker Compose)
1. From `module_6` run:
```bash
docker compose up --build
```
2. Wait for `db` and `rabbitmq` to become healthy (Compose healthchecks are configured).
3. Visit `http://localhost:8080` and use the UI buttons to enqueue tasks.

Useful Docker commands
```bash
docker compose build --no-cache web worker
docker compose up -d
docker compose logs -f web
docker compose exec web python -m pylint src/
```

Notes on dependencies
- Each service uses its own `requirements.txt` (see `src/web/requirements.txt` and `src/worker/requirements.txt`). This is intentional — images are built per-service.
- The project requires `psycopg[binary]` so that code importing `psycopg` works within the slim Python image. If you see `ModuleNotFoundError: No module named 'psycopg'`, ensure `psycopg[binary]` is installed in the service image.

Architecture and verification (what to check)
- Compose services:
   - `db` (Postgres) persists data in named volume `pgdata`.
   - `rabbitmq` provides message broker and management UI.
   - `web` publishes tasks to the `tasks` exchange (via `publisher.publish_task`).
   - `worker` consumes from the queue and runs two handlers: `scrape_new_data` (runs the scraper and inserts new rows) and `recompute_analytics` (recomputes and caches analytics in `analytics_cache`).
- Message flow: `web` publishes JSON messages with `kind` and `payload` to the `tasks` exchange. `worker` binds a durable queue and processes messages, acking on success and nack/rejecting on failure.

Verification steps
1. Start Compose and confirm services are healthy:
    - `docker compose ps` and `docker compose logs db rabbitmq`.
2. Open RabbitMQ UI at `http://localhost:15672` and inspect exchanges/queues.
3. Open the Flask UI at `http://localhost:8080` and click **Pull Data** → check worker logs for a received `scrape_new_data` task.
4. After a scrape completes, confirm rows in Postgres via `docker compose exec db psql -U postgres -c "select count(*) from applicants;"`. 