#!/usr/bin/env bash

set -e
set -x

if [ -x ".venv/bin/coverage" ]; then
  COVERAGE_BIN=".venv/bin/coverage"
else
  COVERAGE_BIN="coverage"
fi

coverage_title="coverage"
pytest_args=()

for arg in "$@"; do
  if [[ "$arg" == Coverage\ for\ * ]] && [ "${#pytest_args[@]}" -eq 0 ] && [ "${coverage_title}" = "coverage" ]; then
    coverage_title="$arg"
    continue
  fi
  pytest_args+=("$arg")
done

if [ "${#pytest_args[@]}" -eq 0 ]; then
  "${COVERAGE_BIN}" run -m pytest tests/
else
  "${COVERAGE_BIN}" run -m pytest "${pytest_args[@]}"
fi
"${COVERAGE_BIN}" report
"${COVERAGE_BIN}" html --title "${coverage_title}"
