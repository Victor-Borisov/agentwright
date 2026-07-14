#!/usr/bin/env python3
"""Agentwright friction collector (called by collect-friction.sh).

Reads the hook JSON from stdin (no size limits, unlike env vars), appends ONE
minimal JSONL line to a per-day-per-session pending file.

Privacy contract (Anthropic Software Directory Policy §1.D/§1.F):
  - records only: event kind, tool name, a locally derived failure CATEGORY,
    project basename, timestamp
  - command text is used transiently to derive the category and never stored

Never breaks the session: swallows every error, exits 0.
"""
import json
import os
import re
import sys
from datetime import datetime

CLASSES = [
    ("test",    r"\b(pytest|jest|vitest|mocha|rspec|phpunit|ctest|tox|go\s+test|cargo\s+test|"
                r"dotnet\s+test|npm\s+(run\s+)?test|yarn\s+(run\s+)?test|pnpm\s+(run\s+)?test|"
                r"make\s+test|python3?\s+-m\s+(pytest|unittest))\b"),
    ("lint",    r"\b(eslint|ruff|flake8|pylint|prettier|black|isort|clippy|golangci-lint|"
                r"shellcheck|stylelint|mypy|npm\s+run\s+lint|yarn\s+(run\s+)?lint)\b"),
    ("build",   r"\b(npm\s+run\s+build|yarn\s+(run\s+)?build|pnpm\s+(run\s+)?build|make\b|cmake|"
                r"cargo\s+build|go\s+build|dotnet\s+build|mvn|gradlew?|tsc\b|webpack|"
                r"vite\s+build|docker\s+build|msbuild)"),
    ("install", r"\b(npm\s+(i|ci|install)|yarn\s+add|pnpm\s+(add|i|install)|pip3?\s+install|"
                r"apt(-get)?\s+install|brew\s+install|cargo\s+add|dotnet\s+add)\b"),
    ("git",     r"(^|&&|;)\s*git\b"),
]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    event = (sys.argv[1] if len(sys.argv) > 1 else "unknown")[:30]
    session = re.sub(r"[^a-zA-Z0-9-]", "", str(data.get("session_id", "nosession")))[:12] or "nosession"
    project = os.path.basename(str(data.get("cwd", "")).rstrip("/"))[:40] or "unknown"
    tool = str(data.get("tool_name", ""))[:40]

    category = ""
    if event == "tool_failure" and tool == "Bash":
        command = str((data.get("tool_input") or {}).get("command", ""))
        category = "other"
        for name, pattern in CLASSES:
            if re.search(pattern, command):
                category = name
                break

    now = datetime.now().astimezone()  # local time, one clock for ts AND file date
    line = {"v": 1, "ts": now.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event, "project": project}
    if tool:
        line["tool"] = tool
    if category:
        line["category"] = category

    pending = os.path.expanduser("~/.claude/agentwright/pending")
    os.makedirs(pending, exist_ok=True)
    day = now.strftime("%Y-%m-%d")
    with open(os.path.join(pending, f"pending-{day}-{session}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
