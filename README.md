# Kiizama

Kiizama is a full-stack platform for creator and brand intelligence, Instagram scraping workflows, and AI-assisted analysis.

Source repository: https://github.com/QuietVenom/kiizama

## Technology Stack and Features

### Backend

- [FastAPI](https://fastapi.tiangolo.com) for the API.
- [Pydantic v2](https://docs.pydantic.dev) and pydantic-settings for validation and configuration.
- [SQLModel](https://sqlmodel.tiangolo.com) + [Alembic](https://alembic.sqlalchemy.org) for relational models and migrations.
- [PostgreSQL](https://www.postgresql.org) for transactional relational data.
- [MongoDB](https://www.mongodb.com) for Instagram profile snapshots and async scrape jobs.
- [Playwright](https://playwright.dev/python/) for scraping execution.
- [OpenAI API](https://platform.openai.com/docs/overview) for enrichment/analysis.
- JWT authentication and role-aware endpoints.
- [Sentry](https://sentry.io) support.

### Frontend

- [React 19](https://react.dev) + [TypeScript](https://www.typescriptlang.org) + [Vite](https://vitejs.dev).
- [Chakra UI v3](https://chakra-ui.com) for components.
- [TanStack Router](https://tanstack.com/router) and [TanStack Query](https://tanstack.com/query).
- Generated API client with [`@hey-api/openapi-ts`](https://heyapi.dev/openapi-ts/get-started).
- [Biome](https://biomejs.dev) for lint/format.
- [Playwright](https://playwright.dev) end-to-end tests.

### Platform and DevOps

- [Docker Compose](https://www.docker.com) for local orchestration and test stacks.
- [uv](https://docs.astral.sh/uv/) for Python dependency and environment management.
- Optional `scrape_worker` process/service for asynchronous jobs.
- [Pytest](https://pytest.org) and Playwright for automated testing.
- CI/CD support with GitHub Actions and Fly.io (`fly.*.toml`).

## How To Use It

### 1) Clone the repository

```bash
git clone https://github.com/QuietVenom/kiizama.git
cd kiizama
```

### 2) Configure environment variables

```bash
cp .env.example .env
```

Update at least:

- `SECRET_KEY`
- `SECRET_KEY_IG_CREDENTIALS`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_PASSWORD` (if using split Postgres vars)
- `MONGODB_URL`
- `OPENAI_API_KEY`

### 3) Start local stack

```bash
docker compose watch
```

### 4) Open local services

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

### 5) Run async worker (optional)

From repository root:

```bash
backend/.venv/bin/python -m scrape_worker.main
```

Or with Docker profile:

```bash
docker compose --profile worker watch
```

## Configure

Configuration lives in `.env` and is consumed by Docker Compose, backend and worker.

### Core

- `PROJECT_NAME`
- `ENVIRONMENT` (`local`, `staging`, `production`)
- `FRONTEND_HOST` (authenticated app origin used by backend-generated links)
- `VITE_API_URL` (frontend API base URL for Docker/frontend envs)
- `BACKEND_CORS_ORIGINS`

### Security and auth

- `SECRET_KEY`
- `SECRET_KEY_IG_CREDENTIALS`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `SYSTEM_ACCESS_TOKEN_EXPIRE_MINUTES`
- `SYSTEM_ADMIN_EMAIL` (optional)
- `SYSTEM_ADMIN_PASSWORD` (optional)

### Databases

Recommended URL variables:

- `DATABASE_URL`
- `DATABASE_URL_PRODUCTION_INTERNAL`

Fallback split Postgres variables:

- `POSTGRES_SERVER`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

MongoDB:

- `MONGODB_URL`
- `MONGODB_KIIZAMA_IG`

### AI and scraping

- `OPENAI_API_KEY`
- `REPUTATION_OPENAI_TIMEOUT_SECONDS`
- `REPUTATION_OPENAI_MAX_RETRIES`

### Email

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_TLS`
- `SMTP_SSL`
- `EMAILS_FROM_EMAIL`

### Async worker variables

Required (or fallback-compatible):

- `IG_SCRAPE_WORKER_MONGODB_URL` (fallback: `MONGODB_URL`)
- `IG_SCRAPE_WORKER_SECRET_KEY_IG_CREDENTIALS` (fallback: `SECRET_KEY_IG_CREDENTIALS`)
- `IG_SCRAPE_WORKER_OPENAI_API_KEY` (fallback: `OPENAI_API_KEY`)

Optional tuning:

- `IG_SCRAPE_WORKER_MONGODB_KIIZAMA_IG`
- `IG_SCRAPE_WORKER_ID`
- `IG_SCRAPE_WORKER_POLL_SECONDS`
- `IG_SCRAPE_WORKER_HEARTBEAT_SECONDS`
- `IG_SCRAPE_WORKER_LEASE_SECONDS`
- `IG_SCRAPE_WORKER_MAX_ATTEMPTS`
- `IG_SCRAPE_WORKER_ERROR_MAX_LEN`

### Observability and images

- `SENTRY_DSN`
- `DOCKER_IMAGE_BACKEND`
- `DOCKER_IMAGE_FRONTEND`

### Generate secret keys

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Input Variables

The current project input variables are the `.env` keys listed above and in `.env.example`.

Use `.env.example` as baseline for each environment (`local`, `staging`, `production`) and provide secrets through your deployment platform.

## Backend Development

Backend docs: [backend/README.md](./backend/README.md).

## Frontend Development

Frontend docs: [frontend/README.md](./frontend/README.md).

## Deployment

Deployment docs: [deployment.md](./deployment.md).

## Development

General development docs: [development.md](./development.md).

## License

This project is licensed under the terms of the MIT license.
