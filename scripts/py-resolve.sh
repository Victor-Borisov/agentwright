# Shared python resolver — source it, don't execute it: `. "${DIR}/py-resolve.sh"`.
# Sets PY to a runnable python >= 3.8, or to "" when none exists. The caller owns
# the failure behavior (silent exit for hooks, loud error for /log, error json for
# the scan), so this file decides nothing beyond the interpreter.
#
# Why not `command -v python3`: Windows ships an App Execution Alias named python3
# that resolves on PATH, prints a Store advert and exits without running anything.
# A lookup-based probe picks it and every caller then fails down its own error path.
# The only reliable probe is executing the candidate — but spawning the dead alias
# costs hundreds of milliseconds, and the friction collector rides PostToolUse, the
# one high-volume hook (MAINTAINING: keep its handler trivial). So the result is
# cached in state/py: a warm call is one read plus one stat, and the alias is paid
# at most once a day, not once per tool call.
#
# Cache staleness: `-x` alone would trust a path forever, including a shim whose
# underlying python was later downgraded below 3.8 — a silent no-op reintroduced
# through the cache. So the cache carries the day it was probed (same YYYY-MM-DD
# day-marker convention as session-start.sh's once-a-day version check) and is
# re-probed on the first use of a new day. The day comes from bash's builtin
# printf '%(...)T' (no process spawn); on a bash too old for it, the daily
# re-probe is skipped and only the stat check remains. Recovery from a poisoned
# or stale cache is always: delete state/py.

PY=""
_aw_state="${HOME:-}/.claude/agentwright/state"
_aw_cache="${_aw_state}/py"
_aw_today="$(printf '%(%Y-%m-%d)T' -1 2>/dev/null || :)"

if [ -n "${HOME:-}" ] && [ -f "$_aw_cache" ]; then
  { IFS= read -r PY; IFS= read -r _aw_day; } < "$_aw_cache" 2>/dev/null || :
  _aw_day="${_aw_day:-}"
  if [ -z "$PY" ] || [ ! -x "$PY" ]; then
    PY=""
  elif [ -n "$_aw_today" ] && [ "$_aw_day" != "$_aw_today" ]; then
    PY=""
  fi
fi

if [ -z "$PY" ]; then
  for _aw_cand in python3 python; do
    _aw_path="$(command -v "$_aw_cand" 2>/dev/null)" || continue
    [ -n "$_aw_path" ] || continue
    if "$_aw_path" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
      PY="$_aw_path"
      if [ -n "${HOME:-}" ]; then
        mkdir -p "$_aw_state" 2>/dev/null || :
        printf '%s\n%s\n' "$PY" "$_aw_today" 2>/dev/null > "$_aw_cache" || :
      fi
      break
    fi
  done
fi

unset _aw_state _aw_cache _aw_cand _aw_path _aw_day _aw_today 2>/dev/null || :
