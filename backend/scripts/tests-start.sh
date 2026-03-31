#! /usr/bin/env bash
set -e
set -x

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${BACKEND_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python"
fi

if [ -x ".venv/bin/alembic" ]; then
  ALEMBIC_BIN=".venv/bin/alembic"
else
  ALEMBIC_BIN="alembic"
fi

if [ -z "${TEST_DATABASE_URL:-}" ] && [ -f "${ROOT_DIR}/.env" ]; then
  export TEST_DATABASE_URL="$(
    "${PYTHON_BIN}" - <<PY
from pathlib import Path

env_path = Path(r"${ROOT_DIR}/.env")
for raw_line in env_path.read_text().splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key == "TEST_DATABASE_URL":
        cleaned = value.strip().strip('"').strip("'")
        print(cleaned)
        break
PY
  )"
fi

if [ -z "${TEST_DATABASE_URL:-}" ]; then
  echo "TEST_DATABASE_URL is required to run tests safely." >&2
  exit 1
fi

export DATABASE_URL="${TEST_DATABASE_URL}"
export RATE_LIMIT_ENABLED="${RATE_LIMIT_ENABLED:-false}"

"${PYTHON_BIN}" app/tests_pre_start.py
"${ALEMBIC_BIN}" upgrade head
"${PYTHON_BIN}" app/initial_data.py

bash scripts/test.sh "$@"
