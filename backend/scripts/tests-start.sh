#! /usr/bin/env bash
set -e
set -x

if [ -n "${TEST_DATABASE_URL}" ]; then
  export DATABASE_URL="${TEST_DATABASE_URL}"
fi

python app/tests_pre_start.py

bash scripts/test.sh "$@"
