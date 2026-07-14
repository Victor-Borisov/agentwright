---
description: >
  Show the user's current Agentwright Score instantly — read-only, no recomputation,
  no dialog. Use when the user wants to display or share their score/level ("show my
  score", "what's my level", screen-sharing with colleagues), or checks progress
  between assessments. For recomputing the score, use the score skill instead.
allowed-tools: "Bash, Read"
---

# Agentwright — show the scorecard

Display the persisted score fast and pretty. NEVER recompute, NEVER start a dialog,
NEVER modify anything. One integrity check + one read + one rendered card.

Respond in the `language` from `~/.claude/agentwright/config.json` if set, otherwise
in the user's language.

## Procedure

1. Run: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/card_integrity.py check`
2. Read `~/.claude/agentwright/scorecard.json`.
3. Render, honoring the check result:

- `no-scorecard` → no card exists yet: suggest `/agentwright:score` (~10 min) and stop.
- `sealed-ok` → render normally.
- `unsealed` → render, with one closing line: the card predates integrity sealing;
  the next `/agentwright:score` run will seal it.
- `MODIFIED-OUTSIDE-AGENTWRIGHT` → do NOT render the numbers. State plainly: the
  scorecard was changed outside Agentwright, so this plugin will not display it;
  run `/agentwright:score` to recompute from facts. No exceptions — this rule is
  what makes a displayed number mean "computed by the plugin".

## Render format

A compact terminal card, in this spirit (markdown, no giant ASCII art):

> **Agentwright Score: 72 ±3 — Agent Builder** · assessed 2026-07-02 (11 days ago)
> Axes: landscape 0.8 · judgment 0.7 · oversight 0.6 · outcome 0.75
> Projects: backend-api 91 · data-jobs 88 (capped by S1)
> Trend: 65 → 72 over 3 runs · 2 fixes verified, 1 awaiting signal
> Verified locally by Agentwright vX.Y.Z; self-assessed, not a third-party certification.

Rules:
- Headline score with its precision band and level, then date with age. If the card
  is older than ~6 weeks, add "consider re-scoring".
- Axes on one line; skip axes that are null/not assessed.
- One line per project score, with caps named.
- Trend from `history[]` (skip if single entry); count `actions[]` verified vs pending.
- The self-assessed disclaimer line is MANDATORY — it protects the user from
  overclaiming in front of an audience, and the plugin from certifying what it cannot.
- Nothing else. No growth plan, no coaching, no questions — this is a display window,
  the audience may be watching a shared screen.
