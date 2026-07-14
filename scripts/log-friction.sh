#!/usr/bin/env bash
# Agentwright manual friction logger.
# Usage: log-friction.sh 'short note about what was annoying'
# Appends a user-authored note to today's journal. The note is the user's own
# deliberate input (not conversation data), capped and sanitized.

set -u
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "agentwright: python3 not found — note NOT logged" >&2
  exit 1
fi

NOTE="${1:-}" PROJECT_DIR="$(pwd)" "$PY" - <<'PYEOF' || { echo "agentwright: write failed — note NOT logged" >&2; exit 1; }
import json, os, re
from datetime import datetime

note = os.environ.get("NOTE", "").strip()
note = re.sub(r"[\x00-\x1f\x7f]", " ", note)[:200]
if not note:
    raise SystemExit(0)

project = os.path.basename(os.environ.get("PROJECT_DIR", "").rstrip("/"))[:40] or "unknown"
now = datetime.now().astimezone()
line = {
    "v": 1,
    "ts": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "event": "manual",
    "project": project,
    "note": note,
}
day = now.strftime("%Y-%m-%d")
pending = os.path.expanduser("~/.claude/agentwright/pending")
os.makedirs(pending, exist_ok=True)
with open(os.path.join(pending, f"pending-{day}-manual.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(line, ensure_ascii=False) + "\n")
print(f"Logged: {note}")
PYEOF
