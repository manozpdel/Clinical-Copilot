#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
FAILED=0

check() {
    local name="$1"
    local url="$2"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
    if [ "$status" = "200" ]; then
        echo "[OK]   $name ($url) -> $status"
    else
        echo "[FAIL] $name ($url) -> $status"
        FAILED=1
    fi
}

check "Frontend"     "$BASE_URL/index.html"
check "API Health"   "$BASE_URL/health"
check "API Version"  "$BASE_URL/api/version"

if [ "$FAILED" -eq 1 ]; then
    echo "One or more health checks failed."
    exit 1
fi

echo "All health checks passed."