---
description: >
  Log a friction note into the Agentwright journal the moment something annoys the
  user. Use when the user wants to record a friction, complains about a recurring
  annoyance in passing ("this took three tries again", "it keeps forgetting to run
  tests"), or explicitly runs the log command with a note. Manual notes are the
  highest-signal friction source for the next coach review.
argument-hint: "[what was annoying]"
allowed-tools: "Bash"
---

# Agentwright — log a friction note

Capture ONE short friction note into the journal, in the moment, with zero ceremony.

## Procedure

1. Take the note text from the user's words. If the skill was invoked from a passing
   complaint rather than an explicit command, distill the complaint into one factual
   sentence (what recurs, where) — in English, since journal artifacts are English —
   and keep it under 200 characters.
2. Run: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/log-friction.sh '<note>'` — ALWAYS wrap the
   note in SINGLE quotes and strip any single quotes from the note text first
   (never double quotes: `$(...)` or backticks inside would execute).
   If the script prints "NOT logged" or exits non-zero, tell the user the note
   was NOT saved and why — never confirm a phantom write.
3. Confirm in one line what was logged — in the `language` from
   `~/.claude/agentwright/config.json` if set, otherwise in the user's language. Never
   ask about language here (logging must stay instant; score/coach handle the setup).
   If the invocation
   came from a passing complaint, make clear it was logged so the user knows
   ("Logged for the next coach review: …").

## Rules

- One note per event; do not editorialize, do not add advice here. Advice belongs to
  `/agentwright:coach`, which will group and review these notes.
- Never log anything the user did not say or clearly imply — the journal must stay
  trustworthy.
- Do not log secrets, tokens, or file contents inside the note.
