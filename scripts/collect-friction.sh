#!/usr/bin/env bash
# Agentwright friction collector — thin wrapper.
# Streams the hook JSON from stdin straight into collect_friction.py (stdin has
# no size limits, unlike env vars). Fail silent: a hook must never block work.
# Note: `exec` replaces the shell, so the python exit code propagates to the hook
# runner as-is — there is no way to force exit 0 after a successful exec.

set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
. "${DIR}/py-resolve.sh"
[ -n "$PY" ] || exit 0
exec "$PY" "${DIR}/collect_friction.py" "${1:-unknown}" 2>/dev/null
