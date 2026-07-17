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
3. Run: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/score_trajectory.py` for the trajectory
   block (sparklines are precomputed — render them verbatim, do not invent glyphs).
4. Render, honoring the check result:

- `no-scorecard` → no card exists yet: suggest `/agentwright:score` (~10 min) and stop.
- `sealed-ok` → render normally.
- `unsealed` → render, with one closing line: the card predates integrity sealing;
  the next `/agentwright:score` run will seal it.
- `MODIFIED-OUTSIDE-AGENTWRIGHT` → do NOT render the numbers. State plainly: the
  scorecard was changed outside Agentwright, so this plugin will not display it;
  run `/agentwright:score` to recompute from facts. No exceptions — this rule is
  what makes a displayed number mean "computed by the plugin".

## Render format

A compact terminal card, in this spirit (markdown, no giant ASCII art). The
trajectory block appears only when `score_trajectory.py` reports `runs >= 2`:

> **Agentwright Score: 78 ±3 — Agent Builder** · assessed 2026-07-17 (today)
>
> Trajectory (5 runs)
> · score&nbsp;&nbsp;&nbsp;▁▃▅▆█&nbsp;&nbsp;62 → 78 (+16)
> · friction ▇▆▄▃▁&nbsp;&nbsp;8.1 → 2.3 per 100 prompts ↓ good
> · axes&nbsp;&nbsp;&nbsp;&nbsp;landscape ▁▃▅▆█ rising · judgment ▁▁▅▅█ flat · oversight ▁▃▅▇█ rising · outcome ▁▃▅▆█ rising
> · fixes&nbsp;&nbsp;&nbsp;4 verified, 1 awaiting signal
>
> Verified locally by Agentwright vX.Y.Z; self-assessed, not a third-party certification.

Rules:
- **Headline** — score with its precision band and level, then date with age. If the
  card is older than ~6 weeks, add "consider re-scoring".
- **Trajectory** (from `score_trajectory.py`) — render the precomputed `spark` strings
  VERBATIM; never fabricate or "improve" glyphs. Show `score`, `friction`, `axes`,
  `fixes` lines. For friction, LOWER is better — a `falling` trend is good (say so).
  If `friction.available` is false, omit the friction line (its snapshot only fills in
  from score runs that recorded it — a couple of runs in). If `runs < 2`
  (`note: single_run`/`no_runs`), skip the whole trajectory block and show only the
  headline + a line like "trajectory builds from your second score run"; still show the
  `fixes` tally if present. Numbers are the truth; the sparkline is illustrative — say
  nothing the numbers don't support.
- **No project list.** `/show` is a screen-share surface and must NOT print per-repo
  names or scores — that would leak the user's whole repository inventory onto a shared
  screen. Per-project readiness lives in the `/agentwright:score` report (private), not
  here. (If the user asks for a repo signal in `/show`, the only allowed form is a
  name-free aggregate — "N repos, median X, most capped by S2" — never the names.)
- The **self-assessed disclaimer** line is MANDATORY — it protects the user from
  overclaiming in front of an audience, and the plugin from certifying what it cannot.
- Nothing else. No growth plan, no coaching, no questions — this is a display window,
  the audience may be watching a shared screen.
