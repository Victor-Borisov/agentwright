---
description: >
  Stuck retrospective — turn a session that went in circles into an upstream fix. Use
  when the user says they thrashed, got stuck, "went round in circles", didn't like how
  the model behaved, or wants a session reviewed for what to improve; or when the coach
  flags a thrash. The user may PASTE the whole conversation into the command and the
  model reviews all of it; if they invoke it empty, ask them to paste it.
argument-hint: "[paste the whole conversation to review]"
allowed-tools: "Bash, Read"
---

# Agentwright — stuck retrospective

Reviews a session the user was unhappy with and finds the UPSTREAM fix (fuzzy target,
no plan, too big, stale context, patching-the-patch, wrong lever). The one thing the
plugin cannot see on its own is prompt/approach quality — transcripts are off-limits
(Anthropic Software Directory Policy §1.F). So the material comes from the USER: they
paste the dialog into this command; the model works only with that.

**Privacy hard line.** Work ONLY from text the user pasted into this command (and the
plugin's own journal). NEVER read `~/.claude/projects/` or any transcript/file to get
the conversation. Do NOT persist the pasted dialog anywhere — analyze it in the moment
and write only the derived English lesson to the scorecard.

**Dialog language.** Read `~/.claude/agentwright/config.json`; conduct the dialog in
`language` if set, else the user's language. Artifacts (scorecard) stay English.

## Procedure

### 1. Do you have material to review?

- **Text was pasted with the command** (the user dropped a conversation in) → go to §2,
  Analyze. Take the WHOLE thing as given; the user will not curate or trim it — do not
  ask them to find "the relevant part."
- **Empty invocation** (no text — e.g. a newcomer just trying the command) → ASK for it,
  don't guess: briefly say what `/retro` does and request the input the skill needs:
  *"Paste the conversation you'd like me to review — the whole thing is fine, I'll find
  where it could improve. Or, if there's no transcript but you just felt stuck, tell me
  what happened and I'll work from the journal."* Then STOP and wait. Do not run an
  analysis on nothing.

### 2. Analyze the pasted dialog

Read all of it and surface, yourself, where it could have gone better — the user asked
you to find it, not to be quizzed:
- ambiguous/underspecified prompts (target not pinned);
- wrong turns pursued, over-complication, going in circles;
- missed levers (plan mode, decomposition/subagent, `/rewind`, a needed guarantee).

Map findings to the thrash taxonomy in `${CLAUDE_PLUGIN_ROOT}/references/thrash.md`
(T1 ambiguous target · T2 no plan · T3 too big · T4 stale context · T5 patching the
patch · T6 wrong lever). Name the most UPSTREAM cause first; a real session often
stacks two — lead with the earliest, land one change, not a lecture.

**Cross-check with the journal, don't just trust the dialog.** Run
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/session_shapes.py` (add `--archive --days 30` if
thin). If the pasted account conflicts with a HARD signal — the dialog reads "tests kept
failing" but `failure_ratio[test].ratio < 0.3`, or "I planned it" but
`capabilities.plan_mode.used == false` — surface the conflict, don't paper over it
(scoring.md § Confidence grading, the `contradicted` case).

**Judgment first.** Before giving your read, ask: "what do you think would have stopped
the loop?" — same judgment-training rule as the coach. Then offer the upstream lever
with its tradeoff.

### 3. Empty-and-narrating fallback (only if the user had no text to paste)

Run `session_shapes.py`, take the strongest `thrash_sessions` entry, reflect the SHAPE
non-judgmentally ("55 turns, a 4-failure test burst, ratio 0.83 — that shape usually
means it looped"), then ask ONE open question — "what were you doing, where did it start
going in circles?" — and proceed from their answer as in §2 (taxonomy, judgment-first).

### 4. Land exactly one change and record it

- If the lever has an artifact (plan-mode habit, a CLAUDE.md decomposition/acceptance
  rule, a hook) and the user agrees, help apply it and record in
  `~/.claude/agentwright/scorecard.json` → `actions[]`: `{friction: "thrash: <cause>",
  lever, date, expected: "<thrash/burst/ratio metric from thrash.md> drops",
  rationale: "<why this lever fixes this cause — the hypothesis>", verified: null}`.
  Record immediately (an applied fix without an entry is an orphan).
- If it is pure craft with no artifact (e.g. T1 "define done first"), record it as a
  landscape teaching: set the relevant `levers{}` entry to `taught` with a short note —
  do NOT mint a fake `actions[]` entry with a metric it cannot move.
- Preserve everything else; do not reseal or recompute the score (that is `/score`'s
  job). Do NOT write the pasted dialog anywhere — only the lesson.

### 5. Close straight

One line: the next `/agentwright:coach` will check (Step 0) whether the thrash/burst
rate for this class actually fell — effect, not opinion. Never end with a grade of the
user's prompting; that is not something this tool measures.
