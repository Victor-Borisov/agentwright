---
description: >
  Stuck retrospective — turn a session that went in circles into an upstream fix.
  Use when the user says they thrashed, got stuck, "went round in circles", spent too
  long on something, or suspects their approach/prompting was off; or when the
  session-start reminder / coach flags a thrash. Detects the STUCK SHAPE from journal
  metadata (never reads prompts), then finds the cause WITH the user from what they
  volunteer, and lands one upstream lever.
allowed-tools: "Bash, Read"
---

# Agentwright — stuck retrospective

The one thing the plugin cannot see is prompt/approach quality — transcripts are
off-limits (Anthropic Software Directory Policy §1.F). So this skill does NOT read
what the user wrote. It detects that a session went in circles from SHAPE, then helps
the user find the upstream cause from what THEY tell it, and lands one lever. Keep the
framing straight throughout: the shape is observed; the cause comes from the user's
account; the prompt is never graded.

**Dialog language.** Read `~/.claude/agentwright/config.json`; conduct the dialog in
`language` if set, else the user's language. Artifacts (scorecard) stay English.

## Procedure

### 1. Find the stuck session (shape only)

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/session_shapes.py` (add `--archive --days 30`
if the recent window is thin). Read `thrash_sessions`:

- If the user named a session or a recent one is present, take it (most recent, or the
  one with a burst + highest stuck-category ratio).
- If `thrash_sessions` is empty but the user invoked this manually ("I got stuck"),
  that is fine — skip straight to step 3 and work purely from their account. Absence
  of a detected shape is NOT "you didn't struggle"; some thrash leaves no burst.

### 2. Reflect the shape — non-judgmentally

State the observable evidence and label it as shape, not judgment:
"Session X: 55 turns, a 4-failure `test` burst in 12 min, ratio 0.83, 2 compactions.
That shape usually means the work looped. I can't see what you wrote — so tell me the
part I can't: …"

### 3. One open question

Ask exactly one: **"What were you trying to get done, and where did it start going in
circles?"** Everything downstream uses only this answer. Do not interrogate; one
question, then listen.

**Do not accept a self-report the journal contradicts** (scoring.md § Confidence
grading). If the user's account conflicts with a HARD signal — they say "the tests kept
failing" but `failure_ratio[test].ratio < 0.3` (mostly green), or "I planned it out" but
`capabilities.plan_mode.used == false` — do not agree and do not override; note the
conflict plainly and ask which sessions they mean. The retrospective is only as good as
the account, and an unchallenged inaccuracy sends it to the wrong cause.

### 4. Judgment first, then the lever

Ask "what do you think would have stopped the loop?" BEFORE offering your read (same
judgment-training rule as the coach). Then map their account to the thrash taxonomy in
`${CLAUDE_PLUGIN_ROOT}/references/thrash.md` (T1 ambiguous target · T2 no plan · T3 too
big · T4 stale context · T5 patching the patch · T6 wrong lever) and propose the most
UPSTREAM matching lever with its tradeoff. If two causes stack, name the earliest one
first; land one change, not a lecture.

### 5. Land exactly one change and record it

- If the lever has an artifact (plan-mode habit, a CLAUDE.md decomposition/acceptance
  rule, a hook), and the user agrees, help apply it and record in
  `~/.claude/agentwright/scorecard.json` → `actions[]`: `{friction: "thrash: <cause>",
  lever, date, expected: "<thrash/burst/ratio metric from thrash.md> drops",
  rationale: "<why this lever fixes this thrash cause — the hypothesis>",
  verified: null}`. Record immediately (an applied fix without an entry is an orphan).
- If it is pure craft with no artifact (e.g. T1 "define done first"), record it as a
  landscape teaching: set the relevant `levers{}` entry to `taught` and leave a short
  note — do NOT mint a fake `actions[]` entry with a metric it cannot move.
- Preserve everything else in the scorecard; do not reseal or recompute the score here
  (that is `/score`'s job).

### 6. Close straight

One line: the next `/agentwright:coach` will check (Step 0) whether the thrash/burst
rate for this class actually fell — effect, not opinion. Never end with a grade of the
user's prompting; that is not something this tool measures.
