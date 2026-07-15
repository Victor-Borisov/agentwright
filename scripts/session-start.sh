#!/usr/bin/env bash
# Agentwright session-start alarm ("the hook wakes, it does not work").
# Fast filesystem-only check. Three duties, all cheap and fail-silent:
#   1. Refresh the cached Claude Code version in the BACKGROUND (at most once
#      a day) — SessionStart stdin carries no version field, so we ask the CLI.
#   2. Notify ONCE per version if Claude Code is ahead of what the knowledge
#      base is calibrated for.
#   3. If pending FRICTION events exist from before today and no review
#      happened today, inject a one-line reminder. Silent otherwise.
#
# Cadence markers (turn, stop, permission_request) are denominators for the
# coach, not friction — they never trigger the alarm by themselves.
#
# Never blocks, never analyzes, always exits 0.

set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${HOME}/.claude/agentwright"
PENDING_DIR="${DATA_DIR}/pending"
FLAG_DIR="${DATA_DIR}/flags"
STATE_DIR="${DATA_DIR}/state"
TODAY="$(date +%Y-%m-%d)"
VER_FILE="${STATE_DIR}/cc-version"

# Drain stdin so the hook pipe never blocks (we don't need its fields here).
cat >/dev/null 2>&1 || true

# ---------- 0. one-time welcome on first run after install ----------
if [ ! -f "${FLAG_DIR}/welcomed" ] && [ ! -f "${DATA_DIR}/scorecard.json" ]; then
  mkdir -p "$FLAG_DIR" 2>/dev/null && : > "${FLAG_DIR}/welcomed" 2>/dev/null
  echo "Agentwright is installed. Get your baseline: run /agentwright:score (short dialog, ~10 min; it will first ask which language to speak with you). After that just work normally — friction is journaled automatically; when something annoys you, capture it with /agentwright:log."
fi

# ---------- 0b. one-time "what's new" after a plugin version change ----------
# No network: the plugin path carries the version, so a changed
# plugin.json version means an update landed. First-ever run writes the marker
# silently (the welcome above already spoke); only a genuine version CHANGE
# announces. We cannot detect that a NEWER version exists upstream without a
# network call (forbidden) — this only reports updates the user already pulled.
PVER_FILE="${STATE_DIR}/plugin-version"
PLUGIN_JSON="${SCRIPT_DIR}/../.claude-plugin/plugin.json"
NEW_PVER="$(grep -o '"version"[[:space:]]*:[[:space:]]*"[0-9][0-9.]*"' "$PLUGIN_JSON" 2>/dev/null | grep -o '[0-9][0-9.]*' | head -1)"
if [ -n "$NEW_PVER" ]; then
  OLD_PVER=""
  [ -f "$PVER_FILE" ] && OLD_PVER="$(head -c 20 "$PVER_FILE" 2>/dev/null | tr -cd '0-9.')"
  if [ "$OLD_PVER" != "$NEW_PVER" ]; then
    mkdir -p "$STATE_DIR" 2>/dev/null && printf '%s' "$NEW_PVER" > "${PVER_FILE}.tmp" 2>/dev/null && mv -f "${PVER_FILE}.tmp" "$PVER_FILE" 2>/dev/null
    [ -n "$OLD_PVER" ] && echo "Agentwright updated to v${NEW_PVER}. What changed: https://github.com/Victor-Borisov/agentwright/blob/main/BACKLOG.md"
  fi
fi

# ---------- 1. background version refresh (at most once per day) ----------
if [ ! -f "${STATE_DIR}/version-checked-${TODAY}" ] && command -v claude >/dev/null 2>&1; then
  mkdir -p "$STATE_DIR" 2>/dev/null && : > "${STATE_DIR}/version-checked-${TODAY}" 2>/dev/null
  (
    v="$(claude --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
    [ -n "$v" ] && printf '%s' "$v" > "${VER_FILE}.tmp" 2>/dev/null && mv -f "${VER_FILE}.tmp" "$VER_FILE" 2>/dev/null
  ) >/dev/null 2>&1 &
fi

# ---------- 2. one-time staleness notice (uses the cached version) ----------
CC_VER=""
[ -f "$VER_FILE" ] && CC_VER="$(head -c 20 "$VER_FILE" 2>/dev/null | tr -cd '0-9.')"
if [ -n "$CC_VER" ] && [ ! -f "${FLAG_DIR}/staleness-${CC_VER}" ]; then
  CAL_FILE="${SCRIPT_DIR}/../references/calibration.json"
  CAL_VER="$(grep -o '"calibrated_for_claude_code"[[:space:]]*:[[:space:]]*"[0-9][0-9.]*"' "$CAL_FILE" 2>/dev/null | grep -o '[0-9][0-9.]*' | head -1)"
  cc_major="${CC_VER%%.*}"; cc_rest="${CC_VER#*.}"; cc_minor="${cc_rest%%.*}"
  cal_major="${CAL_VER%%.*}"; cal_rest="${CAL_VER#*.}"; cal_minor="${cal_rest%%.*}"
  ok=true
  for n in "$cc_major" "$cc_minor" "$cal_major" "$cal_minor"; do
    case "$n" in ''|*[!0-9]*) ok=false ;; esac
  done
  if [ "$ok" = true ] && [ "$CC_VER" != "${CC_VER#*.*.}" ] 2>/dev/null \
     && [ $((cc_major * 1000 + cc_minor)) -gt $((cal_major * 1000 + cal_minor)) ]; then
    mkdir -p "$FLAG_DIR" 2>/dev/null && : > "${FLAG_DIR}/staleness-${CC_VER}" 2>/dev/null
    echo "Agentwright: your Claude Code is ${CC_VER}, but this plugin's knowledge base is calibrated for ${CAL_VER}.x — recently added capabilities may be missing from the checklist. Consider updating the plugin."
  fi
fi

# ---------- 3. friction reminder ----------
[ -d "$PENDING_DIR" ] || exit 0
[ -f "${FLAG_DIR}/reviewed-${TODAY}" ] && exit 0

COUNT=0
DAYS=0
for f in "$PENDING_DIR"/pending-*.jsonl; do
  [ -e "$f" ] || break
  base="$(basename "$f")"
  fday="${base#pending-}"
  fday="${fday:0:10}"
  if [ "$fday" != "$TODAY" ]; then
    n="$(grep -cE '"event": ?"(tool_failure|permission_denied|compact|manual)"' "$f" 2>/dev/null)"
    n="${n%%[!0-9]*}"; n="${n:-0}"
    if [ "$n" -gt 0 ]; then
      COUNT=$((COUNT + n))
      DAYS=$((DAYS + 1))
    fi
  fi
done

[ "$COUNT" -eq 0 ] && exit 0

echo "Agentwright: ${COUNT} friction signal(s) accumulated in ${DAYS} session file(s) since your last review. Run /agentwright:coach to review them, verify past fixes, and update your score."
exit 0
