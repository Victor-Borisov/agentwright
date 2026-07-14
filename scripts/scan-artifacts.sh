#!/usr/bin/env bash
# Thin wrapper so skills and users have one stable entry point.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
command -v python3 >/dev/null 2>&1 || { echo '{"error":"python3 not installed"}'; exit 0; }
exec python3 "${DIR}/scan_artifacts.py" "$@"
