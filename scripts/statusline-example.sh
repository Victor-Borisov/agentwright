#!/usr/bin/env bash
# OPTIONAL statusline example: shows your Agentwright Score next to session info.
# Claude Code cannot install statuslines from plugins — add it yourself:
#
#   ~/.claude/settings.json:
#   { "statusLine": { "type": "command",
#       "command": "bash <path-to-plugin>/scripts/statusline-example.sh" } }
#
# Reads Claude Code's statusline JSON from stdin, appends the score from the scorecard.

set -u
command -v python3 >/dev/null 2>&1 || exit 0

STATUS_JSON="$(cat 2>/dev/null || true)"

STATUS_JSON="$STATUS_JSON" python3 - <<'PYEOF' 2>/dev/null || true
import json, os

try:
    data = json.loads(os.environ.get("STATUS_JSON") or "{}")
except Exception:
    data = {}

parts = []
model = (data.get("model") or {}).get("display_name")
if model:
    parts.append(model)
ctx = (data.get("context_window") or {}).get("used_percentage")
if ctx is not None:
    parts.append(f"ctx {ctx}%")

card_path = os.path.expanduser("~/.claude/agentwright/scorecard.json")
try:
    with open(card_path, encoding="utf-8") as f:
        card = json.load(f)
    if card.get("score") is not None:
        parts.append(f"AW {card['score']}/100 ({card.get('level', '?')})")
except Exception:
    pass

print(" | ".join(parts))
PYEOF
