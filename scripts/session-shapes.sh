#!/usr/bin/env bash
# Thin wrapper for session_shapes.py so skills never invoke an interpreter by name
# (a PATH `python3` can be a dead Windows alias — see py-resolve.sh).
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
. "${DIR}/py-resolve.sh"
[ -n "$PY" ] || { echo '{"error":"no runnable python 3.8+ found"}'; exit 0; }
exec "$PY" "${DIR}/session_shapes.py" "$@"
