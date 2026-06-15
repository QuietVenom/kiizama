# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

`AGENTS.md` above is the canonical operational guide (commands, repo map, project rules, testing notes). What follows is the cross-component architecture that is otherwise spread across `development.md`, `backend/README.md`, and `frontend/README.md`.

## Commands quick reference

- Backend tests (spins up isolated Postgres/Redis containers, migrates, seeds, runs pytest, tears down): `bash scripts/test-local.sh backend`
- Single backend test: `bash scripts/test-local.sh backend tests/unit/core/test_config.py -x` (extra args pass through to pytest; paths are relative to `backend/` because the harness runs pytest from there)
- Frontend non-E2E tests (Vitest): `bash scripts/test-local.sh frontend` or a single file: `bash scripts/test-local.sh frontend tests/component/routes/test_login_form.tsx`
- Playwright E2E: `bash scripts/test-local.sh playwright` (needs `docker compose up -d --wait backend` if running `npm run test:e2e` directly)
- Everything (pre-commit checks + backend + Playwright): `bash scripts/test-local.sh all`
- Backend lint/typecheck (mypy + Ruff): `cd backend && uv run bash scripts/lint.sh`
- Frontend lint (mutating — Biome with `--write --unsafe`): `cd frontend && npm run lint`
- Regenerate the frontend API client after backend API contract changes: `./scripts/generate-client.sh`

## Architecture

Four Python/TS components share one repo. The two `packages/*` libraries are path dependencies consumed by both the backend and the worker — changes there affect both runtimes.

- `backend/` — FastAPI app. HTTP routes live in `backend/app/api/routes/` and must stay thin; business logic lives in feature modules under `backend/app/features/<feature>/` (billing, ig_scraper_jobs, job_control, openai, brand_intelligence, rate_limit, user_events, ...). Each feature follows a layered layout documented in `backend/README.md`: `service.py` (use-case facade) → `repository.py` (DB/Redis access), with `models.py` (SQLModel tables, never exposed as API contracts), `schemas.py`, `clients/` (external systems: Stripe, OpenAI, Apify), `keys.py` (Redis key builders), `policies.py`, `templates/`.
- `scrape_worker/` — standalone async worker process (separate `pyproject.toml`, runs via `backend/.venv/bin/python -m scrape_worker.main`). Consumes queued scrape jobs, runs Playwright scraping + OpenAI enrichment, persists results, then calls back into the backend HTTP API to terminalize jobs.
- `packages/core` (`kiizama_core`) — shared SQL/Redis primitives, the job-control queue/lease/heartbeat machinery, and user-event streams.
- `packages/scrape_core` (`kiizama_scrape_core`) — the Instagram scraper v2 engine (browser/session/stealth/parsers/persistence) and Apify integration. Scraper v2 runtime behavior is configured via `IG_SCRAPER_V2_*` env vars, not API payloads.
- `frontend/` — React 19 + Vite + Chakra UI v3, TanStack Router/Query. `frontend/src/client` is generated from the backend OpenAPI spec — never edit it by hand. The pre-push hook regenerates and verifies it when backend contracts change; if it dirties `frontend/src/client`, commit the regenerated files before pushing.

### Async job lifecycle (the core data-flow to understand)

Instagram scrape jobs flow through a split-ownership model:

1. `POST /api/v1/ig-scraper/jobs` enqueues a job in Redis and returns a job id.
2. **Redis is the source of truth for live job lifecycle**: queueing, lease ownership, heartbeat, retry/reclaim, and terminal dedupe (Lua scripts in `kiizama_core.job_control`).
3. The worker leases jobs from Redis, heartbeats while scraping/enriching, and persists scrape results to **Postgres**, which holds the queryable job projection served by `GET /api/v1/ig-scraper/jobs/{job_id}`.
4. **Only the backend accepts terminal completion** (worker calls back via `scrape_worker/backend_client.py`) and emits the final SSE event to the user.

### Local stack

`docker compose watch` runs Postgres, Redis, backend (:8000), and frontend (:5173). Backend or frontend containers can be stopped and replaced by local processes on the same ports (`fastapi dev app/main.py` / `npm run dev`). The worker is opt-in: `docker compose --profile worker watch`, or run it on the host. Inside Docker the worker uses Compose service names (`redis`, `postgres`, `backend`); on the host it uses `localhost` URLs from the root `.env`. `docker-compose.test.yml` is the isolated test overlay used by `scripts/test-local.sh`.

## Conventions worth knowing

- Python is managed with `uv` (`uv sync` in `backend/`); use interpreter `backend/.venv/bin/python`.
- Migrations: Alembic, run inside the backend container.
- New backend tests go under `backend/tests/{unit,integration,contract}/...` — not the legacy `tests/api/routes`, `tests/features`, or `tests/crud` paths. Backend testing is integration-first; mock only true external boundaries.
- New frontend tests use Vitest + React Testing Library (`frontend/tests/{unit,component,contract}`); no new `node:test` coverage; Playwright (`frontend/tests/e2e`) is for real browser/app flows only.
- Some dependency names still say `*_collection` but are session-backed (not Mongo collections).
- Pre-commit hooks (ruff, mypy, biome, secrets scan) install via `uv run --project backend pre-commit install` (and `--hook-type pre-push`).
