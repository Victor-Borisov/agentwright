#!/usr/bin/env bash
# Thin wrapper so skills and users have one stable entry point.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
. "${DIR}/py-resolve.sh"
[ -n "$PY" ] || { echo '{"error":"no runnable python 3.8+ found"}'; exit 0; }
exec "$PY" "${DIR}/scan_artifacts.py" "$@"
