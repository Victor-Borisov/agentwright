#!/usr/bin/env bash
# Thin wrapper for card_integrity.py so skills never invoke an interpreter by name
# (a PATH `python3` can be a dead Windows alias — see py-resolve.sh).
# Exit codes pass through unchanged: 0 sealed-ok, 3 no scorecard, 4 no seal,
# 5 mismatch. With no runnable python it prints its own marker and exits 1,
# which no card_integrity branch uses.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
. "${DIR}/py-resolve.sh"
[ -n "$PY" ] || { echo "no-python" >&2; exit 1; }
exec "$PY" "${DIR}/card_integrity.py" "$@"
