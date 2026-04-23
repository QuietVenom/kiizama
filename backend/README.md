# Kiizama - Backend

## Requirements

- [Docker](https://www.docker.com/)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency and virtualenv management

## Quick Start (Docker Compose)

From repository root, follow the main local setup in [../development.md](../development.md):

```bash
docker compose watch
```

Backend API will be available at:

- http://localhost:8000
- http://localhost:8000/docs

## Stripe billing

Stripe billing is configured in the backend, not the frontend.

Required vars when working on billing flows:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_BASE_PRICE_ID`

Optional:

- `BILLING_TRIAL_DAYS`

Webhook route:

- `POST /api/v1/billing/webhooks/stripe`

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

Current ownership model:

- Redis owns queueing, live job state, lease ownership, reclaim, and terminal dedupe.
- Postgres stores the persisted scrape data and the queryable job projection returned by `GET /ig-scraper/jobs/{job_id}`.
- The backend accepts the final job completion and emits the SSE notification.

From repository root:

```bash
backend/.venv/bin/python -m scrape_worker.main
```

Related endpoints:

- `POST /api/v1/ig-scraper/jobs`
- `GET /api/v1/ig-scraper/jobs/{job_id}`
- `POST /api/v1/ig-scraper/profiles/batch` (synchronous flow)

Optional Docker profile:

```bash
docker compose --profile worker watch
```

## Backend Feature Modules

Backend business logic is organized under `backend/app/features/<feature_name>/`.
API routes stay in `backend/app/api/routes/` and should call feature services instead of owning business rules directly.

Feature modules should be cohesive around a business capability: billing, rate limiting, job control, reports, OpenAI workflows, user events, etc. A feature may expose one public facade while splitting internal implementation into smaller modules as it grows.

Recommended structure:

```text
backend/app/
├── api/
│   └── routes/
│       └── <feature_name>.py
└── features/
    └── <feature_name>/
        ├── __init__.py
        ├── service.py
        ├── repository.py
        ├── models.py
        ├── schemas.py
        ├── constants.py
        ├── errors.py
        ├── services/
        │   ├── access_read.py
        │   ├── access_write.py
        │   └── workflow_step.py
        ├── clients/
        │   └── external_provider.py
        ├── classes/
        │   └── data.py
        ├── types/
        │   ├── base.py
        │   └── provider_impl.py
        ├── templates/
        │   └── report.html
        ├── keys.py
        ├── policies.py
        ├── scripts.py
        └── worker_runtime.py
```

Not every feature needs every file. Add only the files that serve a current use case.

Layer mapping:

- `api/routes/<feature_name>.py`: HTTP boundary. Parse inputs, enforce auth/dependencies, call services, and return response schemas. Keep business logic out of routes.
- `features/<feature_name>/__init__.py`: public import surface for the feature. Re-export only stable functions/classes meant for other modules.
- `service.py`: feature facade or primary use-case layer. Coordinate repositories, domain helpers, external clients, events, and transaction-aware workflows.
- `services/`: internal service modules when one `service.py` would become too broad. Split by use case, not by arbitrary technical category.
- `repository.py`: database/Redis persistence and query logic. Keep session, SQLModel, Redis key access, joins, filters, and projections here.
- `models.py`: SQLModel table models or persistence-specific models owned by the feature. Do not use table models as public API contracts.
- `schemas.py`: Pydantic/SQLModel schemas for request payloads, responses, service inputs, or serialized outputs.
- `constants.py`: domain constants, feature codes, event names, default limits, and shared literal values.
- `errors.py`: feature-specific exceptions, typed errors, or helpers that translate domain failures into predictable app errors.
- `clients/`: external-system boundaries such as Stripe, OpenAI, Apify, email providers, object storage, or third-party HTTP APIs.
- `classes/`: pure domain containers, dataclasses, serializers, parsers, prompt payload builders, and deterministic transformations.
- `types/`: implementation families or base types, such as report generators, worker types, provider strategies, or abstract worker contracts.
- `templates/`: feature-owned prompt, HTML, email, or report templates. Shared report/prompt assets may also live under `app/features/templates/`.
- `keys.py`: Redis, cache, lock, idempotency, or stream key builders.
- `policies.py`: reusable decision logic: permission rules, quota policies, fail-open/fail-closed behavior, or access calculations.
- `scripts.py`: feature-owned script definitions, commonly Redis Lua scripts. Do not put operational shell commands here.
- `worker_runtime.py`: orchestration for long-running or background worker execution owned by the feature.

Design rules:

- Prefer one feature module per business capability, not per endpoint.
- Keep routes thin and put orchestration in services.
- Keep persistence in repositories or tightly scoped data-access helpers.
- Mock only external boundaries in tests; use integration tests for routes, services with DB/Redis, and repositories.
- Create optional directories only when the feature actually needs them.
- If a module is scaffold-only or illustrative, do not keep it under `app/features`; only production code should live there.

## Linting and Tests

From repository root, prefer the repo harness:

```bash
bash scripts/test-local.sh backend
```

Run a specific backend test file or selection by passing pytest args through the
harness:

```bash
bash scripts/test-local.sh backend backend/tests/integration/api/test_health_api.py
bash scripts/test-local.sh backend backend/tests/unit/core/test_config.py -x
```

The backend harness starts isolated local Postgres and Redis containers, runs
`uv sync`, applies migrations, seeds initial data, executes pytest, writes
coverage, and tears the containers down.

For linting from `./backend`:

```bash
uv run bash scripts/lint.sh
```

`scripts/lint.sh` runs `mypy` on `app` and runs Ruff check/format validation on `app` and `scripts`.

### Backend Test Structure

```text
backend/
├── tests/
│   ├── contract/       # OpenAPI and frontend-consumed API contracts
│   │   ├── helpers.py
│   │   └── test_*_contract.py
│   ├── factories/      # Thin domain factories for reusable setup
│   ├── fixtures/       # Shared DB, auth, Redis, and external-boundary fixtures
│   ├── integration/
│   │   ├── api/        # FastAPI HTTP tests with auth, validation, persistence
│   │   ├── core/       # DB/Redis/core integration behavior
│   │   ├── repositories/
│   │   │   ├── billing/
│   │   │   ├── instagram/
│   │   │   ├── job_control/
│   │   │   ├── rate_limit/
│   │   │   └── ...
│   │   ├── scripts/    # Startup/prestart scripts against real infra
│   │   └── services/   # Services that collaborate with DB/Redis/repositories
│   ├── unit/
│   │   ├── app/        # App wiring, handlers, utility behavior
│   │   ├── core/       # Deterministic core helpers and policies
│   │   ├── scrape_core/
│   │   ├── scrape_worker/
│   │   └── services/   # Pure parsing, rendering, coercion, branch logic
│   └── utils/          # Legacy/shared pytest helpers used by fixtures/tests
└── htmlcov/            # Generated coverage HTML output
```

New backend tests should not be added under old structures such as
`tests/api/routes`, `tests/features`, or `tests/crud`.

### Test Type Rules

- Use `integration/api` for HTTP contract behavior: status codes, auth,
  permissions, validation, response shape, and persisted effects.
- Use `integration/repositories` for SQLModel/Postgres and Redis persistence
  semantics.
- Use `integration/services` when a service coordinates repositories, DB,
  Redis, idempotency, queues, rate limits, or usage reservations.
- Use `unit` for deterministic logic only: parsing, normalization, schemas,
  payload coercion, rendering, policy branches, and error translation.
- Use `contract` to protect OpenAPI paths, methods, response content types, and
  response/request shapes consumed by the generated frontend client.

Backend testing is integration-first. Prefer real Postgres and Redis for
behavior that crosses persistence, transactions, queues, streams, rate limits,
or repository boundaries.

Mock only true external boundaries:

- Stripe
- Resend/email
- OpenAI
- Apify
- Playwright/PDF generation
- third-party HTTP services

Do not mock internal collaborators when a realistic integration test is
practical.

### Test Naming And Style

- Use `feature_condition_expected_result` names.
- Keep one main behavior per test.
- Use Arrange / Act / Assert structure.
- Assert persisted state when the feature changes DB or Redis state.
- Keep factories thin; do not hide business logic inside factories.
- Prefer function-scoped fixtures unless a broader scope is clearly safe and
  materially faster.

### Running Tests With An Existing Stack

If the backend test stack is already running and you only want to run pytest:

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/app_test \
REDIS_URL=redis://localhost:6379/0 \
uv run bash scripts/tests-start.sh
```

Pass additional pytest args if needed:

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/app_test \
REDIS_URL=redis://localhost:6379/0 \
uv run bash scripts/tests-start.sh tests/integration/api/test_health_api.py -x
```

`scripts/tests-start.sh` sets `DATABASE_URL` from `TEST_DATABASE_URL`, disables
rate limiting by default, runs `app/tests_pre_start.py`, applies Alembic
migrations, seeds initial data, and then delegates to `scripts/test.sh`.

`scripts/test.sh` runs pytest under coverage and writes `backend/htmlcov`.

### Local Test Infrastructure

```bash
bash scripts/test-local.sh backend
```

This creates ephemeral test services:

- Postgres: `postgresql+psycopg://postgres:postgres@localhost:55432/app_test`
- Redis: `redis://localhost:6379/0`

Both services are created only for the local test run and removed afterward.
Do not use Fly Redis, production Postgres, or any non-test database URL for
backend tests. The suite keeps `assert_safe_test_database_url` enabled to guard
against unsafe database targets.

GitHub Actions follows the same model: the backend test workflow starts
ephemeral Postgres and Redis services, runs migrations and tests, uploads
`backend/htmlcov`, then tears the stack down.

### API Contract Changes

If backend API paths, methods, request schemas, response schemas, status codes,
or content types change, update contract tests and regenerate the frontend
client from repository root:

```bash
./scripts/generate-client.sh
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
