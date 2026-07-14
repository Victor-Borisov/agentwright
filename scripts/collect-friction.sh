#!/usr/bin/env bash
# Agentwright friction collector — thin wrapper.
# Streams the hook JSON from stdin straight into collect_friction.py (stdin has
# no size limits, unlike env vars). Fail silent, exit 0 always.

set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || exit 0
exec "$PY" "${DIR}/collect_friction.py" "${1:-unknown}" 2>/dev/null || exit 0
