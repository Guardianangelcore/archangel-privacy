#!/usr/bin/env bash
# Run the backend test suite the way the agents do: preview URL env + founder password from the env.
# Usage: FOUNDER_TEST_PASSWORD=... backend/run_tests.sh [pytest args]
set -euo pipefail
cd "$(dirname "$0")"
URL="$(grep -E '^EXPO_PUBLIC_BACKEND_URL=' ../frontend/.env | cut -d= -f2-)"
export EXPO_PUBLIC_BACKEND_URL="$URL"
export EXPO_BACKEND_URL="$URL"
export REACT_APP_BACKEND_URL="$URL"
exec python3 -m pytest -q tests/ -p no:cacheprovider "$@"
