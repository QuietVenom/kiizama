# AGENTS.md

Quick operational guidance for agents working in `kiizama`.

Use this file as a map, not a manual. Follow the linked project docs for full setup and deployment details.

## Read These First

- `development.md`: local setup, `.env`, Docker flows, local frontend/backend replacement, worker runtime, test overlays, pre-commit, and pre-push generated-client behavior
- `deployment.md`: supported deployment target, Fly.io configs, production env expectations, and CI/CD boundaries
- `README.md`: top-level stack and product overview
- `backend/README.md`: backend-specific workflow, tests, and migrations
- `frontend/README.md`: frontend-specific workflow, client generation, and Playwright usage

## Repo Map

- `backend`: FastAPI API and backend business logic
- `frontend`: React/Vite app, authenticated UI, and blog build
- `scrape_worker`: standalone async scrape worker runtime
- `packages/scrape_core`: shared scraping, persistence, Redis, and job-control primitives
- `scripts`: repo-standard orchestration entrypoints

Backend code is feature-oriented and generally follows route/service/repository boundaries.

Some dependency names still use `*_collection`, but current implementations are session-backed rather than Mongo-style collections.

## Preferred Commands

- Start the main local stack: `docker compose watch`
- Run frontend locally instead of Docker: `docker compose stop frontend && cd frontend && npm run dev`
- Run backend locally instead of Docker: `docker compose stop backend && cd backend && fastapi dev app/main.py`
- Install Chromium for local scraping work when needed: `backend/.venv/bin/python -m playwright install chromium`
- Run the async worker locally: `backend/.venv/bin/python -m scrape_worker.main`
- Run the Docker worker profile: `docker compose --profile worker watch`
- Run backend checks: `cd backend && uv run bash scripts/lint.sh`
- Run backend tests with the repo harness: `bash scripts/test-local.sh backend`
- Run Playwright tests with the repo harness: `bash scripts/test-local.sh playwright`
- Run the full local validation flow: `bash scripts/test-local.sh all`
- Refresh the generated frontend API client after backend API contract changes: `./scripts/generate-client.sh`

Use Alembic inside the backend container for schema migrations.

`frontend` lint is mutating: `npm run lint` runs Biome with `--write --unsafe`.

## Project Rules

- Keep backend routes thin. Put business logic in services or domain helpers, not in routes.
- Keep persistence logic in repositories or clearly bounded data-access helpers.
- Follow pragmatic backend design: DRY, KISS, YAGNI, separation of concerns, and pragmatic SOLID.
- Prefer simple procedural or functional logic for straightforward workflows. Use OOP or polymorphism only when it clearly improves clarity, encapsulation, testability, or extensibility.
- For SQLModel-backed work, keep table models separate from API schemas. Do not use `table=True` models as public API contracts.
- Preserve local module patterns unless the task explicitly asks for a broader refactor.
- Do not edit `frontend/src/client` manually. It is generated from the backend OpenAPI contract.
- New non-E2E frontend coverage should follow the repo direction toward `Vitest` plus React Testing Library.
- Do not add new `node:test` frontend coverage.
- Keep Playwright for real browser-level or app-level flows, not isolated component behavior.

## Testing Notes

- Prefer `bash scripts/test-local.sh ...` over bare `pytest` or bare `npx playwright test` for repo validation.
- Backend testing is integration-first by default.
- Mock true external boundaries only when needed. Do not default to mock-heavy internal tests.
- Each confirmed bug fix should add or strengthen regression coverage.
- Pre-push verifies the generated frontend client when backend or client-generation changes are involved. If `frontend/src/client` changes, regenerate it and commit the result before pushing.

## Installed Skills

- `backend-engineering`: backend implementation, refactors, reviews, and architecture guidance
- `fastapi`: FastAPI-specific patterns and conventions
- `frontend-design-engineering`: frontend implementation, refactors, reviews, UX, and design quality
- `kiizama-backend-test-framework`: backend test strategy and backend test additions in this repo
- `kiizama-frontend-test-framework`: frontend test strategy and frontend test additions in this repo
- `kiizama-sqlmodel`: SQLModel models, schemas, relationships, and update-flow patterns in this repo
- `kiizama-tests`: correct execution of the existing repo test suites

## OpenAI Docs

For OpenAI API or Codex questions, prefer the OpenAI Developer Docs MCP server if it is configured. Otherwise, use only official OpenAI documentation domains such as `developers.openai.com` and `platform.openai.com`.

## Maintenance

Keep this file short and current.

Put deeper operational detail in `development.md`, `deployment.md`, repo READMEs, or skills instead of growing this file into a long manual.
