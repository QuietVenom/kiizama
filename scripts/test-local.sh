#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PLAYWRIGHT_TEST_ENV_FILE="$ROOT_DIR/.env.test-local-playwright"
TEST_COMPOSE_FILE="$ROOT_DIR/docker-compose.test.yml"

LOCAL_TEST_DB_URL="postgresql+psycopg://postgres:postgres@localhost:55432/app_test"
DOCKER_TEST_DB_URL="postgresql+psycopg://postgres:postgres@postgres_test:5432/app_test"
LOCAL_TEST_REDIS_URL="redis://localhost:6379/0"
LOCAL_TEST_DB_NAME="app_test"
LOCAL_TEST_DB_USER="postgres"
TEST_COMPOSE_PROJECT="kiizama-test-local"

TARGET="${1:-all}"
if [[ $# -gt 0 ]]; then
  shift
fi

usage() {
  cat <<'EOF'
Usage:
  ./scripts/test-local.sh
  ./scripts/test-local.sh all
  ./scripts/test-local.sh checks
  ./scripts/test-local.sh backend
  ./scripts/test-local.sh backend -x
  ./scripts/test-local.sh backend backend/tests/api/routes/test_ig_profile_snapshots.py -x
  ./scripts/test-local.sh playwright
  ./scripts/test-local.sh playwright --shard=1/4
  ./scripts/test-local.sh playwright tests/example.spec.ts

Targets:
  all         Run pre-commit checks, backend tests, and Playwright tests
  checks      Run only pre-commit checks
  backend     Run backend test flow
  playwright  Run Playwright test flow

Notes:
  - Extra args are passed only to pytest or Playwright for that target.
  - "backend" uses the local Docker Redis container at localhost:6379.
  - "backend" does not require fly redis proxy kiizama-redis.
  - For "backend" with no extra args, this script runs scripts/tests-start.sh.
  - For "backend" with extra args, this script runs pytest directly.
EOF
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

compose_test_stack() {
  local compose_args=(
    -f "$ROOT_DIR/docker-compose.yml"
    -f "$TEST_COMPOSE_FILE"
    -p "$TEST_COMPOSE_PROJECT"
  )

  if [[ -n "${TEST_STACK_ENV_FILE:-}" ]]; then
    compose_args+=(--env-file "$TEST_STACK_ENV_FILE")
    docker compose "${compose_args[@]}" "$@"
  else
    docker compose "${compose_args[@]}" "$@"
  fi
}

cleanup_test_containers() {
  if [[ "${TEST_STACK_STARTED:-0}" != "1" ]]; then
    rm -f "$PLAYWRIGHT_TEST_ENV_FILE"
    return
  fi

  log "Stopping local test containers..."
  compose_test_stack down -v --remove-orphans
  TEST_STACK_STARTED=0
  rm -f "$PLAYWRIGHT_TEST_ENV_FILE"
}

ensure_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "❌ Missing required command: $cmd"
    exit 1
  fi
}

ensure_env_file() {
  if [[ ! -f "$ROOT_DIR/.env" ]]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    log "Created .env from .env.example"
  fi
}

upsert_env_var() {
  local file="$1"
  local key="$2"
  local value="$3"

  if [[ ! -f "$file" ]]; then
    touch "$file"
  fi

  python3 - <<PY
from pathlib import Path

path = Path(r"$file")
key = "$key"
value = "$value"

lines = path.read_text().splitlines() if path.exists() else []
out = []
replaced = False

for line in lines:
    if line.startswith(f"{key}="):
        out.append(f"{key}={value}")
        replaced = True
    else:
        out.append(line)

if not replaced:
    out.append(f"{key}={value}")

path.write_text("\n".join(out) + "\n")
PY
}

prepare_playwright_env_file() {
  cp "$ROOT_DIR/.env" "$PLAYWRIGHT_TEST_ENV_FILE"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "DATABASE_URL" "$DOCKER_TEST_DB_URL"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "TEST_DATABASE_URL" "$DOCKER_TEST_DB_URL"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_SERVER" "postgres_test"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_PORT" "5432"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_DB" "$LOCAL_TEST_DB_NAME"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_USER" "$LOCAL_TEST_DB_USER"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_PASSWORD" "postgres"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_TEST_DB" "$LOCAL_TEST_DB_NAME"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_TEST_USER" "$LOCAL_TEST_DB_USER"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_TEST_PASSWORD" "postgres"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "POSTGRES_TEST_PORT" "55432"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "REDIS_URL" "redis://redis:6379/0"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "RATE_LIMIT_ENABLED" "false"
  upsert_env_var "$PLAYWRIGHT_TEST_ENV_FILE" "CI" ""
}

clean_pycache_linux() {
  if [[ "$(uname -s)" == "Linux" ]]; then
    log "Cleaning __pycache__ directories on Linux..."
    find "$ROOT_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
  fi
}

wait_for_redis() {
  local max_attempts="${1:-30}"
  local attempt=1

  log "Waiting for Redis container to accept connections..."
  while (( attempt <= max_attempts )); do
    if compose_test_stack exec -T redis redis-cli ping >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    ((attempt++))
  done

  echo "❌ Redis did not become ready after ${max_attempts} seconds."
  exit 1
}

wait_for_postgres() {
  local max_attempts="${1:-60}"
  local attempt=1

  log "Waiting for Postgres test container to accept connections..."
  while (( attempt <= max_attempts )); do
    if compose_test_stack exec -T postgres_test \
      pg_isready -U "$LOCAL_TEST_DB_USER" -d "$LOCAL_TEST_DB_NAME" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    ((attempt++))
  done

  echo "❌ Postgres did not become ready after ${max_attempts} seconds."
  exit 1
}

run_checks() {
  log "Running pre-commit checks..."
  ensure_command uv

  cd "$ROOT_DIR"
  uv run --project "$BACKEND_DIR" pre-commit run --all-files
}

run_backend() {
  log "Running backend test flow..."
  ensure_command docker
  ensure_command uv
  ensure_env_file
  clean_pycache_linux

  cd "$ROOT_DIR"

  TEST_STACK_ENV_FILE=""
  compose_test_stack down -v --remove-orphans
  TEST_STACK_STARTED=1
  trap cleanup_test_containers RETURN
  compose_test_stack up -d postgres_test redis
  wait_for_postgres
  wait_for_redis

  cd "$BACKEND_DIR"
  uv sync

  DATABASE_URL="$LOCAL_TEST_DB_URL" \
  REDIS_URL="$LOCAL_TEST_REDIS_URL" \
    uv run bash scripts/prestart.sh

  if [[ $# -gt 0 ]]; then
    log "Running pytest directly with custom args: $*"
    DATABASE_URL="$LOCAL_TEST_DB_URL" \
    TEST_DATABASE_URL="$LOCAL_TEST_DB_URL" \
    REDIS_URL="$LOCAL_TEST_REDIS_URL" \
      uv run pytest "$@"
  else
    log "Running backend CI-like test script..."
    DATABASE_URL="$LOCAL_TEST_DB_URL" \
    TEST_DATABASE_URL="$LOCAL_TEST_DB_URL" \
    REDIS_URL="$LOCAL_TEST_REDIS_URL" \
      uv run bash scripts/tests-start.sh
  fi
}

run_playwright() {
  log "Running Playwright test flow..."
  ensure_command docker
  ensure_command uv
  ensure_command npm
  ensure_env_file
  clean_pycache_linux

  cd "$ROOT_DIR"

  prepare_playwright_env_file

  cd "$BACKEND_DIR"
  uv sync

  cd "$FRONTEND_DIR"
  npm ci

  cd "$ROOT_DIR"
  VIRTUAL_ENV=backend/.venv uv run bash scripts/generate-client.sh

  TEST_STACK_STARTED=1
  TEST_STACK_ENV_FILE="$PLAYWRIGHT_TEST_ENV_FILE"
  compose_test_stack build
  compose_test_stack down -v --remove-orphans
  trap cleanup_test_containers RETURN
  compose_test_stack up -d --wait postgres_test redis backend

  if [[ $# -gt 0 ]]; then
    log "Running Playwright with custom args: $*"
    compose_test_stack run --rm playwright \
      npx playwright test --trace=retain-on-failure "$@"
  else
    log "Running Playwright default suite..."
    compose_test_stack run --rm playwright \
      npx playwright test --trace=retain-on-failure
  fi
}

case "$TARGET" in
  all)
    run_checks
    run_backend
    run_playwright
    ;;
  checks)
    run_checks
    ;;
  backend)
    run_backend "$@"
    ;;
  playwright)
    run_playwright "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "❌ Unknown target: $TARGET"
    echo
    usage
    exit 1
    ;;
esac
