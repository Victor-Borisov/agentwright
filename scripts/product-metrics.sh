#!/usr/bin/env bash
# Thin wrapper for product_metrics.py so the README never tells a user to invoke an
# interpreter by name (a PATH `python3` can be a dead Windows alias — see py-resolve.sh).
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
. "${DIR}/py-resolve.sh"
[ -n "$PY" ] || { echo "agentwright: no runnable python 3.8+ found" >&2; exit 1; }
exec "$PY" "${DIR}/product_metrics.py" "$@"
