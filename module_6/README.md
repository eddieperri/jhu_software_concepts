# Grad Cafe Analytics Dashboard (Module 6)

A containerized microservice version of the Grad Cafe dashboard. The stack includes a Flask web service, a background worker, RabbitMQ, and PostgreSQL orchestrated with Docker Compose.

## Architecture

- `web`: Flask application that renders analytics and publishes tasks to RabbitMQ.
- `worker`: Background consumer that executes `scrape_new_data` and `recompute_analytics` tasks.
- `db`: PostgreSQL database with persistent named volume storage.
- `rabbitmq`: Message broker with the management UI exposed on port `15672`.

## Run Instructions

From the `module_6` directory:

```powershell
docker compose up --build
```

Then visit:

- `http://localhost:8080` for the Flask UI
- `http://localhost:15672` for RabbitMQ management (`guest` / `guest`)

Click **Pull Data** to enqueue a scrape task and **Update Analysis** to enqueue analytics recompute.

## Environment Variables

The stack configures these values automatically inside the containers:

- `RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/`
- `DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres`
- `PYTHONUNBUFFERED=1`

## Notes

- The worker mounts `src/data` read-only for safe ingestion.
- The stack uses a named volume `pgdata` to persist Postgres data.
- Both web and worker containers run as non-root user `1000`.

### Option A: Standard pip Installation
1. Create a standard Python virtual environment:
   `python -m venv venv`
2. Activate the environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. Install the frozen dependencies and the local package in editable mode:
   `pip install -r requirements.txt`
   `pip install -e .`

### Option B: High-Speed uv Installation
1. Create a virtual environment using uv:
   `uv venv`
2. Activate the environment (same as above).
3. Sync the exact environment state and install the local package:
   `uv pip sync requirements.txt`
   `uv pip install -e .`

## Database Configuration (Least Privilege)
This application enforces strict database security. It does not use the default PostgreSQL superuser.
Create a `.env` file in the root directory (use `.env.example` as a template) and provide your credentials:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=thegradcafe
DB_USER=grad_app_user
DB_PASSWORD=your_secure_password


## Running the App
python src/flask_app.py
Navigate to http://127.0.0.1:5000/analysis in your browser.

## Pylint
To verify the linting score, from inside the module_5 folder, run:
pylint src/

## Snyk
We use `snyk test` to scan `requirements.txt` against vulnerability databases to ensure no compromised third-party libraries are introduced.
We could use `snyk code test` to scan our custom Python source code for insecure practices (like hardcoded secrets or SQL injection vulnerabilities). This code has not been tested using such a service.