#! /usr/bin/env bash
set -e
set -x

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${BACKEND_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"

if [ -z "${TEST_DATABASE_URL:-}" ] && [ -f "${ROOT_DIR}/.env" ]; then
  export TEST_DATABASE_URL="$(
    python3 - <<PY
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

python app/tests_pre_start.py

bash scripts/test.sh "$@"
