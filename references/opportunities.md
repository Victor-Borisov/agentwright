# Opportunity matrix

Missed-opportunity detectors: for each Claude Code capability, the observable
signature of a situation where it *would have helped but was not used*. This is the
top-down half of detection — symptom detectors (failures, denials) catch felt pain;
these catch the pain the user cannot feel because the lever is not on their map.

## Detector contract (hard rules)

1. **A detector nominates, it never convicts.** Metadata cannot distinguish "two
   tasks interleaved" from "one big task" — and does not need to. Show the evidence,
   ask the question, let the answer decide.
2. **At most 1–2 opportunity candidates per coach run**, highest-confidence first.
   More turns coaching into a nagging feature tour.
3. **Remember the answer — and the reason.** Every asked opportunity gets a
   scorecard entry (`opportunities[]`) with the user's stated reason: `adopted` /
   `taught` (didn't know — now knows; give the practical task) / `dismissed`.
   Re-ask a `dismissed` one only when its recorded REASON is invalidated by new
   evidence — "those waves are lunch breaks" is invalidated by a mid-wave
   compaction, not by more lunches. Raw amplitude growth alone never re-opens it.
   For scoring, `dismissed` means the lever is KNOWN; full conscious-refusal credit
   is granted only in the `/score` dialog under its quality bar (scoring.md).
4. **Teach at the moment.** The question always carries the mini-lesson: what the
   lever guarantees, what it costs — never a bare "did you know about X?".

Signatures are computed by `scripts/session_shapes.py` (deterministic). Thresholds
below are defaults; tune per user history, never below the floor values.

---

## O1 · Session-per-task splitting (`/clear`, new sessions, `--resume`)

**Helps when:** several unrelated tasks share one session — each task's context
pollutes the others; quality degrades late; returning to task 1 means re-explaining.
**Not when:** one large task with natural pauses; exploratory work that genuinely
builds on everything before it.
**Signature:** one session with `duration ≥ 3h` AND `activity_waves ≥ 2` (gaps
≥ 45 min) AND `compacts ≥ 1`. The compaction conjunct is MANDATORY: context
pollution is the harm being taught, and it is directly observed — without it,
"two waves with a gap" is just a workday with a lunch break, and a false first
nomination would burn this detector via the dismissal memory. Confidence up if
turns ≥ 25.
**Question:** "Session X ran 7h in two waves with a compaction between — was that
more than one task? Separate sessions keep each task's context clean: `/clear`
between tasks, or a new session per task (the old one stays resumable with
`--resume`), or `/compact` with focus instructions if the history matters."
**On adoption:** rule in user CLAUDE.md ("start unrelated tasks with /clear") — L6;
re-detect via falling wave/compact rates.

## O2 · git worktrees for parallel streams

**Helps when:** two agents/sessions work the same repo at once — one checkout means
stepping on each other's edits and branch juggling.
**Not when:** the parallel sessions touch different repos, or one is read-only.
**Signature:** two sessions with overlapping time ranges in the **same project**
(`overlaps[]` non-empty) AND `capabilities.worktree.used == false`. The direct
capability signal is the strong half: precomputed in `unused_lever_warrants`
(`lever: worktree`). If `worktree.used` is true, the user already knows the lever —
do NOT nominate; instead credit landscape (see § Capability signals). Category `git`
failures in the overlap strengthen it.
**Question:** "Yesterday two sessions overlapped in <project> — parallel work in one
checkout? A worktree gives each stream its own directory on its own branch: no
stashing, no collisions. Costs: disk and a one-time habit."

## O3 · Subagents / background tasks for long or bulky work

**Helps when:** big searches, long builds, batch edits burn the main context window
or block the conversation.
**Not when:** short interactive tasks — orchestration overhead exceeds the win.
**Signature:** sessions with `turns ≥ 40`, or `compacts ≥ 2` in a single session,
AND `capabilities.subagent.used == false` (precomputed in `unused_lever_warrants`,
`lever: subagent`). If `subagent.used` is true, don't nominate — credit landscape.
**Question:** "Session X hit N turns and compacted twice. Wide exploration and long
runs can go to a subagent (own context, returns only the conclusion) or a background
task — the main session stays lean. Costs: you review a summary instead of watching
every step."

## O4 · Checkpoints / `/rewind` instead of fixing forward

**Helps when:** the agent is thrashing — repeated failed attempts stacking patches
on patches; rolling back to the last good point is cheaper than repairing.
**Not when:** failures are legitimate iteration on a hard problem.
**Signature:** `failure_burst`: ≥ 3 `tool_failure` of the same category within
15 minutes in one session.
**Question:** "Three test failures in 12 minutes in <project> — was the agent
digging deeper into a hole? After the second failed fix, rewinding to the last good
checkpoint and re-approaching usually beats patching the patch."

## O5 · Package it as a skill / command

**Helps when:** the same kind of work (and the same friction) recurs across days or
projects — a repeatable process living in your head.
**Not when:** genuinely one-off work.
**Signature:** same failure category recurring across ≥ 2 projects, or ≥ 2 `manual`
notes with the same theme within the review window.
**Question:** "This is the third note about <theme>. A repeatable process can become
a skill or slash command — written once, triggered by name or by description, shared
between projects. Costs: an hour to write, occasional description tuning."

## O6 · Automatic feedback loops (hooks) — symptom-driven, see levers L1–L3

Covered by pain detectors (`tool_failure` categories test/lint/build). The teaching
angle when proposing: the ladder — the agent that *sees* the failure immediately
fixes it without being told.

## O7 · Permission tuning — symptom-driven, see lever L4

Covered by `permission_request` rate. Teaching angle: deny-list for the destructive,
allow-list for the routine; prompts should be rare enough to stay meaningful.

## O8 · Context hygiene (`/compact` focus, lean CLAUDE.md) — see lever L7

Covered by `compact` events, but always pair the fix with the *why*: quality
degrades silently as the window fills; compaction is lossy — deliberate hygiene
beats automatic salvage.

## O10 · Plan mode for large changes

**Helps when:** a non-trivial multi-file change runs with no exploration/plan phase —
edits pile up, and a wrong direction is discovered late.
**Not when:** the session was many small independent tasks, or genuinely trivial.
**Signature:** a `turns ≥ 40` session with `capabilities.plan_mode.used == false`
(`unused_lever_warrants`, `lever: plan_mode`). Turn count is a SIZE proxy, not proof
of a single big change — so this always nominates, never convicts.
**Question:** "Session X ran 45 turns with no plan mode. For a big multi-file change,
plan mode separates exploration from editing: Claude proposes the approach, you
approve before a single file changes. Costs: a minute up front. Was this one large
change, or several small ones?"

## O11 · Effort level per task

**Helps when:** every session runs at the same effort regardless of task difficulty —
hard problems under-reasoned, or trivial ones over-spent.
**Not when:** the user's work is genuinely uniform in difficulty.
**Signature:** `effort_distribution` has a single level across sessions of clearly
different shape (some `turns ≥ 40`, some tiny). Effort IS observable (`effort.level`
in the hook payload); MODEL is not (never in metadata — model-per-task stays a
`/score` dialog item, O9).
**Question:** "You ran everything at `high` effort this week, including short
sessions. Effort can be dialed per task (`/effort`): low for quick edits, max for
hard multi-step problems. Was that deliberate?"

## O12 · Configured MCP that is never used

**Helps when:** an MCP server is configured but the journal shows zero `mcp` tool use
over the window — dead config, or a lever forgotten.
**Not when:** the server is genuinely occasional (ask before concluding).
**Signature:** artifact scan reports an MCP server AND `capabilities.mcp.used == false`
across the window.
**Question:** "You have an MCP server configured but haven't used it in N days —
still needed, or worth removing to keep the surface lean?"

## O9 · Dialog-only levers (no reliable metadata signature)

MODEL selection per task, multi-model orchestration, extended thinking,
prerequisite-gate design, review-by-separate-instance: their absence leaves no
trustworthy trace in journal metadata. They are assessed ONLY in the
`/agentwright:score` dialog (items D1–D6) — never inferred from shapes, never nagged
about here. (Contrast: plan mode, subagent, worktree, MCP-use and effort ARE now
observable — O2/O3/O10/O11/O12 — because the tool name / effort level appears in the
hook payload; model does not.) If the score dialog marked a dialog-only lever
`absent`, the coach may bring it up ONCE with a practical task, then it follows the
adopted/taught/dismissed lifecycle.

## Capability signals — positive credit, not just gaps

The same `capabilities` map that powers absence-nomination also CONFIRMS competence:
when `plan_mode` / `subagent` / `worktree` / `mcp` / `lsp` shows `used: true`, the
user demonstrably knows and reaches for that lever. That is direct evidence for the
landscape axis — the `/score` dialog should credit it WITHOUT asking, and the
mastery captcha (scoring.md) may be skipped for a lever the journal shows in active
use. New hooks find gaps AND retire questions.
