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
- `OPENAI_API_KEY`
- `STRIPE_SECRET_KEY` if you want local billing checkout and portal flows
- `STRIPE_BASE_PRICE_ID` if you want checkout sessions to create subscriptions
- `APIFY_API_TOKEN` if you want Apify-based scrape jobs (`POST /api/v1/ig-scraper/jobs/apify`)

For local Stripe webhook handling, also set:

- `STRIPE_WEBHOOK_SECRET`

## Docker Compose

Start the local stack:

```bash
docker compose watch
```

Local service URLs:

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:8000](http://localhost:8000)
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

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
- `Postgres` for persisted scrape results and the queryable job projection

Relevant endpoints:

- `POST /api/v1/ig-scraper/jobs`
- `POST /api/v1/ig-scraper/jobs/apify`
- `GET /api/v1/ig-scraper/jobs/{job_id}`

`POST /api/v1/ig-scraper/jobs` accepts up to 10 usernames plus scraping options and returns a queued job id.

Jobs carry an execution mode that decides which runtime consumes them:

- `worker` jobs (`POST /api/v1/ig-scraper/jobs`) are consumed by the standalone `scrape_worker` process using Playwright scraping. Toggle: `IG_SCRAPER_WORKER_JOBS_ENABLED` (default `true`).
- `apify` jobs (`POST /api/v1/ig-scraper/jobs/apify`) are consumed by an in-process runner inside the backend that scrapes through the Apify API. They require `APIFY_API_TOKEN`. Toggle: `IG_SCRAPER_APIFY_JOBS_ENABLED` (default `true`). Runner tuning lives in the `IG_SCRAPER_APIFY_*` variables in `.env.example`.

A disabled flow returns `503` on its enqueue endpoint. Both flows share the same job status endpoint, billing rules, Redis lifecycle, and Postgres projection.

`GET /api/v1/ig-scraper/jobs/{job_id}` returns:

- `status`: `queued`, `running`, `done`, or `failed`
- `summary`
- `references`
- operational metadata such as `attempts`, `lease_owner`, `leased_until`, and `heartbeat_at`

Ownership rules:

- Redis is the source of truth for live job lifecycle
- Postgres stores the queryable job projection and persisted scrape result
- the backend is the only component that accepts terminal completion and emits the final SSE event

### Worker process

Run the API and worker in separate terminals during local development.

1. Start backend API:

```bash
cd backend
fastapi dev app/main.py
```

1. Start worker:

```bash
backend/.venv/bin/python -m scrape_worker.main
```

The worker consumes queued jobs, maintains lease and heartbeat state in Redis, performs scraping and AI enrichment, persists results, and calls back into the backend for terminalization.

Scraper v2 runtime is configured through environment variables, not API payloads. By default it uses the local IP address outside production. In `ENVIRONMENT=production`, scraper v2 always uses ISP proxy mode, ignores `IG_SCRAPER_V2_USE_ISP_PROXY=false`, and requires `IG_SCRAPER_V2_ISP_PROXY_URLS`. To enable DECODO/ISP proxy sessions locally:

```bash
IG_SCRAPER_V2_USE_ISP_PROXY=true
IG_SCRAPER_V2_ISP_PROXY_URLS=http://<decodo-user>:<decodo-password>@<decodo-host>:<decodo-port>
```

Useful scraper v2 tuning variables:

- `IG_SCRAPER_V2_MAX_CONCURRENT`
- `IG_SCRAPER_V2_MAX_POSTS`
- `IG_SCRAPER_V2_HEADLESS`
- `IG_SCRAPER_V2_TIMEOUT_MS`
- `IG_SCRAPER_V2_LOCALE`
- `IG_SCRAPER_V2_PACING_ENABLED`
- `IG_SCRAPER_V2_PACING_MIN_SECONDS`
- `IG_SCRAPER_V2_PACING_MAX_SECONDS`
- `IG_SCRAPER_V2_WARMUP_MIN_SECONDS`
- `IG_SCRAPER_V2_WARMUP_MAX_SECONDS`

Leave warm-up vars empty to use defaults: local mode uses a shorter warm-up range, while proxy mode uses a longer cold browser warm-up before the first Instagram navigation.

### Worker with Docker Compose (optional)

An optional local service `scrape_worker` is available in `docker-compose.override.yml` behind the `worker` profile.

```bash
docker compose --profile worker watch
docker compose logs -f scrape_worker
```

When the worker runs inside Docker, Compose overrides host-local `.env` URLs and uses service names instead: `redis`, `postgres`, and `backend`. When running the worker directly on the host, use `localhost`/`127.0.0.1` URLs. Recreate containers after changing Compose environment wiring:

```bash
docker compose down
docker compose --profile worker watch
```

## Docker Compose files and env vars

`docker-compose.yml` is the shared base for local and test stacks.

`docker-compose.override.yml` is for local development only. It adds dev-friendly behavior such as:

- source sync for backend and worker code
- backend `--reload`
- local port publishing

`docker-compose.test.yml` is the isolated test stack overlay.

The local test scripts call Docker Compose explicitly with the test file. To run backend tests manually against the isolated Postgres + Redis stack (test paths are relative to `backend/`):

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d postgres_test redis
cd backend
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/app_test \
REDIS_URL=redis://localhost:6379/0 \
bash scripts/tests-start.sh tests/integration/api/test_ig_scraper_api.py tests/integration/api/test_events_api.py
```

After changing env vars, restart the stack:

```bash
docker compose watch
```

## The .env file

The top-level `.env` file is the local source of truth for Docker Compose, backend, and worker settings.

For frontend development outside Docker, Vite still reads `frontend/.env` or shell-provided `VITE_*` variables. The repository `.env.example` provides the default `VITE_API_URL` value used by Docker-based flows.

## Stripe billing local setup

Stripe billing configuration is backend-only in this repository.

Required backend vars:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_BASE_PRICE_ID`

Optional backend var:

- `BILLING_TRIAL_DAYS` (`7` by default)

Local billing webhook URL:

- [http://localhost:8000/api/v1/billing/webhooks/stripe](http://localhost:8000/api/v1/billing/webhooks/stripe)

If you use the Stripe CLI locally, forward events with:

```bash
stripe listen --forward-to http://localhost:8000/api/v1/billing/webhooks/stripe
```

Billing webhook events currently expected by the backend:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `customer.subscription.paused`
- `customer.subscription.resumed`
- `customer.subscription.trial_will_end`
- `invoice.paid`
- `invoice.payment_failed`
- `invoice.upcoming`
- `refund.created`
- `refund.updated`
- `refund.failed`
- `charge.refunded` as temporary compatibility during webhook migration

## Pre-commits and code linting

This repository uses [pre-commit](https://pre-commit.com/) for linting and formatting.

When you install it, it runs right before making a commit in git. This way it ensures that the code is consistent and formatted even before it is committed.

You can find a file `.pre-commit-config.yaml` with configurations at the root of the project.

### Install pre-commit to run automatically

`pre-commit` is already part of the backend development dependencies, but you could also install it globally if you prefer to, following [the official pre-commit docs](https://pre-commit.com/).

After having the `pre-commit` tool installed and available, you need to "install" it in the local repository, so that it runs automatically before each commit and push.

Using `uv`, you could do it with:

```bash
❯ uv run --project backend pre-commit install
pre-commit installed at .git/hooks/pre-commit
❯ uv run --project backend pre-commit install --hook-type pre-push
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

### Running pre-commit hooks manually

you can also run `pre-commit` manually on all the files, you can do it using `uv` with:

```bash
❯ uv run --project backend pre-commit run --all-files
check for added large files..............................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
ruff check...............................................................Passed
ruff format..............................................................Passed
Detect hardcoded secrets.................................................Passed
backend mypy.............................................................Passed
biome check..............................................................Passed
```
