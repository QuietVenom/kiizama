# Kiizama - Development

## Prerequisites

Create your local env file:

```bash
cp .env.example .env
```

Set required values before running services locally:

- `SECRET_KEY`
- `SECRET_KEY_IG_CREDENTIALS`
- `FIRST_SUPERUSER_PASSWORD`
- `MONGODB_URL`
- `OPENAI_API_KEY`

## Docker Compose

Start the local stack:

```bash
docker compose watch
```

Local service URLs:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

The first startup can take a while because the backend waits for dependencies and runs prestart tasks.

Useful log commands:

```bash
docker compose logs
docker compose logs backend
docker compose logs frontend
```

## Local Development

Docker Compose exposes the backend and frontend on the same ports used by their local dev servers. You can stop one service and replace it with the local process without changing URLs.

Stop frontend container and run Vite locally:

```bash
docker compose stop frontend
cd frontend
npm run dev
```

Stop backend container and run FastAPI locally:

```bash
docker compose stop backend
cd backend
fastapi dev app/main.py
```

If you plan to use Instagram scraping locally, install Playwright Chromium once:

```bash
backend/.venv/bin/python -m playwright install chromium
```

## Async Instagram Scrape Jobs

The project supports asynchronous Instagram scraping jobs with:

- `Redis` for queueing, live job state, lease ownership, heartbeat, retry recovery, and terminal dedupe
- `MongoDB` for the persisted scrape result plus a TTL-backed job projection for queries and history

Relevant endpoints:

- `POST /api/v1/ig-scraper/profiles/batch`
- `POST /api/v1/ig-scraper/jobs`
- `GET /api/v1/ig-scraper/jobs/{job_id}`

`POST /api/v1/ig-scraper/jobs` accepts up to 10 usernames plus the same scraping options as the sync flow. It returns a queued job id.

`GET /api/v1/ig-scraper/jobs/{job_id}` returns:

- `status`: `queued`, `running`, `done`, or `failed`
- `summary`
- `references`
- operational metadata such as `attempts`, `lease_owner`, `leased_until`, and `heartbeat_at`

Ownership rules:

- Redis is the source of truth for live job lifecycle
- MongoDB stores the queryable job projection and persisted scrape result
- the backend is the only component that accepts terminal completion and emits the final SSE event

### Worker process

Run the API and worker in separate terminals during local development.

1. Start backend API:

```bash
cd backend
fastapi dev app/main.py
```

2. Start worker:

```bash
backend/.venv/bin/python -m scrape_worker.main
```

The worker consumes queued jobs, maintains lease and heartbeat state in Redis, performs scraping and AI enrichment, persists results, and calls back into the backend for terminalization.

### Worker with Docker Compose (optional)

An optional local service `scrape_worker` is available in `docker-compose.override.yml` behind the `worker` profile.

```bash
docker compose --profile worker watch
docker compose logs -f scrape_worker
```

## Docker Compose files and env vars

`docker-compose.yml` is the shared base for local and test stacks.

`docker-compose.override.yml` is for local development only. It adds dev-friendly behavior such as:

- source sync for backend and worker code
- backend `--reload`
- local port publishing

`docker-compose.test.yml` is the isolated test stack overlay.

The local test scripts call Docker Compose explicitly with the test file. To run backend tests manually against the isolated Postgres + Redis stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d postgres_test redis
cd backend
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/app_test \
REDIS_URL=redis://localhost:6379/0 \
bash scripts/tests-start.sh backend/tests/api/routes/test_ig_scraper_jobs.py backend/tests/api/routes/test_events.py
```

After changing env vars, restart the stack:

```bash
docker compose watch
```

## The .env file

The top-level `.env` file is the local source of truth for Docker Compose, backend, and worker settings.

For frontend development outside Docker, Vite still reads `frontend/.env` or shell-provided `VITE_*` variables. The repository `.env.example` provides the default `VITE_API_URL` value used by Docker-based flows.

## Pre-commits and code linting

This repository uses [pre-commit](https://pre-commit.com/) for linting and formatting.

When you install it, it runs right before making a commit in git. This way it ensures that the code is consistent and formatted even before it is committed.

You can find a file `.pre-commit-config.yaml` with configurations at the root of the project.

#### Install pre-commit to run automatically

`pre-commit` is already part of the dependencies of the project, but you could also install it globally if you prefer to, following [the official pre-commit docs](https://pre-commit.com/).

After having the `pre-commit` tool installed and available, you need to "install" it in the local repository, so that it runs automatically before each commit and push.

Using `uv`, you could do it with:

```bash
❯ uv run pre-commit install
pre-commit installed at .git/hooks/pre-commit
❯ uv run pre-commit install --hook-type pre-push
pre-commit installed at .git/hooks/pre-push
```

Now whenever you try to commit, e.g. with:

```bash
git commit
```

...pre-commit will run and check and format the code you are about to commit, and will ask you to add that code (stage it) with git again before committing.

Then you can `git add` the modified/fixed files again and now you can commit.

The `pre-push` hook also verifies the generated frontend API client when your branch includes backend or client-generation changes. If it regenerates files under `frontend/src/client`, the push is aborted and you need to:

```bash
git add frontend/src/client
git commit --amend --no-edit  # or create a new commit
git push
```

All other configured hooks continue to run on `pre-commit`; only the generated client verification runs on `pre-push`.

#### Running pre-commit hooks manually

you can also run `pre-commit` manually on all the files, you can do it using `uv` with:

```bash
❯ uv run pre-commit run --all-files
check for added large files..............................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
ruff.....................................................................Passed
ruff-format..............................................................Passed
eslint...................................................................Passed
prettier.................................................................Passed
```
