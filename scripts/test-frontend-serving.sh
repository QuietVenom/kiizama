#!/usr/bin/env bash
set -euo pipefail

# Run against the built Nginx frontend, not Vite. SPA route fallbacks must
# receive the same revalidation policy as an explicit /index.html request.
origin="${1:-http://localhost:5173}"
headers="$(mktemp)"
trap 'rm -f "$headers"' EXIT

for route in / /index.html /creators-search /settings; do
  curl --fail --silent --show-error --dump-header "$headers" \
    --output /dev/null "${origin%/}${route}"
  if ! tr -d '\r' < "$headers" | rg -qi '^cache-control:.*no-cache.*no-store.*must-revalidate'; then
    echo "FAIL: HTML cache policy missing on $route" >&2
    exit 1
  fi
  echo "PASS: HTML revalidation on $route"
done
