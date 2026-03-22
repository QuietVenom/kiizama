#! /usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENT_PATH="frontend/src/client"
MODE="local"
BASE_REF="${GENERATE_CLIENT_BASE_REF:-origin/main}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/check-generated-client.sh --mode local
  bash scripts/check-generated-client.sh --mode ci

Options:
  --mode      local | ci
  --base-ref  git ref used to decide whether local verification is needed
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --base-ref)
      BASE_REF="${2:-}"
      shift 2
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$MODE" != "local" && "$MODE" != "ci" ]]; then
  echo "Invalid mode: $MODE" >&2
  usage >&2
  exit 2
fi

cd "$ROOT_DIR"

client_status() {
  git status --porcelain --untracked-files=all -- "$CLIENT_PATH"
}

branch_has_relevant_changes() {
  if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
    echo "Base ref '$BASE_REF' was not found. Running generated client verification anyway."
    return 0
  fi

  local merge_base
  merge_base="$(git merge-base HEAD "$BASE_REF" 2>/dev/null || true)"
  if [[ -z "$merge_base" ]]; then
    echo "Could not determine a merge-base with '$BASE_REF'. Running generated client verification anyway."
    return 0
  fi

  if git diff --quiet "$merge_base"...HEAD -- \
    backend \
    scripts/generate-client.sh \
    frontend/package.json \
    frontend/package-lock.json \
    frontend/openapi-ts.config.ts; then
    return 1
  fi

  return 0
}

if [[ "$MODE" == "local" ]]; then
  if [[ -n "$(client_status)" ]]; then
    cat <<'EOF'
Generated client files already have local changes. Commit or stash them before pushing.
EOF
    exit 1
  fi

  if ! branch_has_relevant_changes; then
    echo "Skipping generated client verification: no backend/OpenAPI generation changes in this branch."
    exit 0
  fi
fi

echo "Running generated client verification..."
bash scripts/generate-client.sh

if [[ -n "$(client_status)" ]]; then
  if [[ "$MODE" == "ci" ]]; then
    cat <<'EOF'
Generated frontend client is out of date.
Run `./scripts/generate-client.sh`, commit `frontend/src/client`, and push the updated branch.
EOF
  else
    cat <<'EOF'
Generated frontend client changed during pre-push verification.
Run:
  git add frontend/src/client
  git commit --amend --no-edit   # or create a new commit
  git push
EOF
  fi
  exit 1
fi

echo "Generated frontend client is up to date."
