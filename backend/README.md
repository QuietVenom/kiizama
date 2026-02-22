# Kiizama - Backend

## Requirements

- [Docker](https://www.docker.com/)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency and virtualenv management

## Quick Start (Docker Compose)

From repository root, follow the main local setup in [../development.md](../development.md):

```bash
docker compose watch
```

Backend API will be available at:

- http://localhost:8000
- http://localhost:8000/docs

## Local Backend Workflow (without Docker backend service)

From `./backend`:

```bash
uv sync
source .venv/bin/activate
fastapi dev app/main.py
```

Use interpreter `backend/.venv/bin/python` in your editor.

## Async Instagram Scrape Worker

Asynchronous scrape jobs are consumed by `scrape_worker` at repository root.

From repository root:

```bash
backend/.venv/bin/python -m scrape_worker.main
```

Related endpoints:

- `POST /api/v1/ig-scrapper/jobs`
- `GET /api/v1/ig-scrapper/jobs/{job_id}`
- `POST /api/v1/ig-scrapper/profiles/batch` (synchronous flow)

Optional Docker profile:

```bash
docker compose --profile worker watch
```

## Linting and Tests

From `./backend`:

```bash
uv run bash scripts/lint.sh
uv run bash scripts/test.sh
```

If the stack is already running and you only want tests:

```bash
docker compose exec backend bash scripts/tests-start.sh
```

Pass additional pytest args if needed:

```bash
docker compose exec backend bash scripts/tests-start.sh -x
```

### Isolated local Postgres for tests

```bash
docker compose up -d postgres_test
cd backend
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/app_test bash scripts/tests-start.sh
```

## Migrations

Run Alembic commands inside backend container:

```bash
docker compose exec backend bash
alembic revision --autogenerate -m "Describe your schema change"
alembic upgrade head
```

Migration files live in `backend/app/alembic/versions/`.

## Docker Compose Override Notes

`docker-compose.override.yml` is intended for local development only.

Current override behavior includes:

- source sync to container for quick iteration
- backend command override to `fastapi run --reload app/main.py`
- optional worker profile (`scrape_worker`)

## Email Templates

Email templates are under:

- `backend/app/email-templates/src` (sources)
- `backend/app/email-templates/build` (compiled HTML)

Use the VS Code MJML extension to compile `.mjml` into HTML.
