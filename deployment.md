# Kiizama - Deployment

Kiizama no longer documents or supports self-hosted deployment with Docker Compose ingress. The supported deployment target is Fly.io.

CI is handled with GitHub Actions workflows in `.github/workflows`.

## Shared environment variables

Most deployments need the same core settings:

- `ENVIRONMENT=production`
- `PROJECT_NAME`
- `FRONTEND_HOST`
- `BACKEND_CORS_ORIGINS`
- `SECRET_KEY`
- `SECRET_KEY_IG_CREDENTIALS`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `SYSTEM_ADMIN_EMAIL` / `SYSTEM_ADMIN_PASSWORD` when internal worker callbacks are enabled
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_TLS`
- `SMTP_SSL`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `EMAILS_FROM_EMAIL`
- `DATABASE_URL` or `DATABASE_URL_PRODUCTION_INTERNAL`
- `MONGODB_URL`
- `MONGODB_KIIZAMA_IG`
- `OPENAI_API_KEY`
- `SENTRY_DSN` if used

For production links and CORS, keep the current public model:

- backend: `https://api.kiizama.com`
- authenticated frontend: `https://app.kiizama.com`
- marketing frontend: `https://www.kiizama.com`

## Fly.io

This repository includes:

- [fly.backend.toml](./fly.backend.toml)
- [fly.frontend.toml](./fly.frontend.toml)
- [fly.scrape-worker.toml](./fly.scrape-worker.toml)

### Backend

Deploy from repository root:

```bash
fly deploy . --config fly.backend.toml
```

The backend app serves `https://api.kiizama.com` and expects:

- production database and MongoDB settings
- SMTP provider credentials
- app/user/admin secrets

### Frontend

Deploy from `frontend/`:

```bash
fly deploy ./frontend --config ../fly.frontend.toml
```

The frontend build uses:

- `VITE_API_URL=https://api.kiizama.com`

Keep both `www` and `app` routed to the frontend app so Nginx can apply the redirect rules correctly.

### Scrape Worker

Deploy from repository root:

```bash
fly deploy . --config fly.scrape-worker.toml
```

The worker stays private by design and runs:

```bash
python -m scrape_worker.main
```

Required worker-focused vars:

- `IG_SCRAPE_WORKER_MONGODB_URL`
- `IG_SCRAPE_WORKER_REDIS_URL`
- `IG_SCRAPE_WORKER_BACKEND_BASE_URL`
- `IG_SCRAPE_WORKER_SECRET_KEY_IG_CREDENTIALS`
- `IG_SCRAPE_WORKER_OPENAI_API_KEY`
- `IG_SCRAPE_WORKER_SYSTEM_ADMIN_EMAIL`
- `IG_SCRAPE_WORKER_SYSTEM_ADMIN_PASSWORD`

Optional tuning vars:

- `IG_SCRAPE_WORKER_ID`
- `IG_SCRAPE_WORKER_POLL_SECONDS`
- `IG_SCRAPE_WORKER_HEARTBEAT_SECONDS`
- `IG_SCRAPE_WORKER_LEASE_SECONDS`
- `IG_SCRAPE_WORKER_MAX_ATTEMPTS`
- `IG_SCRAPE_WORKER_ERROR_MAX_LEN`

Fallback compatibility remains available through shared vars such as `MONGODB_URL`, `REDIS_URL`, `OPENAI_API_KEY`, and `SYSTEM_ADMIN_EMAIL`.

## GitHub Actions secrets

Current repository-level GitHub Actions secrets:

- `SMOKESHOW_AUTH_KEY`

`GITHUB_TOKEN` is provided automatically by GitHub Actions.

## Generate secret keys

Some values in `.env.example` are insecure placeholders such as `changethis` and `ChangeThis1!`. Generate secure replacements with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Continuous Deployment (CD)

Deployments are managed by the hosting platform configuration in the Fly apps defined by the `fly.*.toml` files.

### GitHub Actions and CD

There are no GitHub Actions deployment workflows in this repository right now.

GitHub Actions are currently used for CI, testing, labeling, conflict detection, and coverage reporting.
