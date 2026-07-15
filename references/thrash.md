# Thrash taxonomy — the upstream fix for going in circles

Used by the `retro` skill and the coach when `session_shapes.thrash_sessions` is
non-empty. A thrash is DETECTED from shape only (a failure burst, or a large session
with a category stuck at a high failure ratio) — never from reading prompts. The cause
is found WITH the user, from what THEY volunteer about the session. Prompt/approach
quality is off-limits to the plugin (Anthropic Software Directory Policy §1.F); the
user brings the content, the plugin brings the taxonomy and the levers.

## The six causes and their upstream lever

Each cause: what the user's own account tends to reveal · the lever that would have
prevented the loop · what the fix costs · the recorded expected effect (so Step-0
verification can confirm the thrash rate actually dropped).

| # | Cause — how the user describes it | Upstream lever | Cost | Expected effect to record |
|---|---|---|---|---|
| T1 | **Ambiguous target** — "I wasn't sure what done looked like", kept redefining success mid-way | Pin acceptance criteria BEFORE work: one sentence of "done =", or a failing test that encodes it | a minute of thought | thrash/burst rate per 100 turns drops for this class |
| T2 | **No plan, dived into editing** — "I just started changing files" on a multi-file change | Plan mode first: explore + propose approach, approve before a file changes (lever: plan_mode) | one plan step | `capabilities.plan_mode.used` rises; large-session bursts drop |
| T3 | **Too big to hold** — "it was one huge task", context filled and quality fell | Decompose: split into steps; hand the wide part to a subagent (own context, returns a summary) | orchestration overhead | `compact` rate + turns-per-task drop |
| T4 | **Stale / wrong context** — "it kept referencing things that changed / weren't there" | Fresh brief: `/clear` + a short facts draft-file of the current truth, instead of resuming stale context | re-briefing cost | `compact` rate drops; fewer wrong-assumption retries |
| T5 | **Patching the patch** — "each fix broke something else, I kept going" | `/rewind` to the last good checkpoint after the SECOND failed fix, then re-approach (lever: rewind, O4) | lose since-checkpoint work | `failure_burst` rate drops |
| T6 | **Wrong lever — needed a guarantee** — "I kept reminding it and it kept forgetting" | Stop asking; install the guarantee: a hook/gate so the failure is impossible, not discouraged (ladder in levers.md) | latency/cycle time | the treated category's `failure_ratio` drops |

## How to land it (both `retro` and coach follow this)

1. Show the SHAPE non-judgmentally ("55 turns, a 4-failure test burst, ratio 0.83, 2
   compactions — that shape usually means the work looped"), and say plainly: this is
   the shape, not a read of what you wrote.
2. Ask ONE open question: "In your words — what were you trying to get done, and where
   did it start going in circles?" Everything downstream uses only this answer.
3. Ask the user's judgment first ("what would've stopped the loop?"), then map their
   account to T1–T6 and offer the upstream lever with its tradeoff.
4. Land exactly ONE change. If it has an artifact (plan-mode habit, a CLAUDE.md
   decomposition rule, a hook), record it in `scorecard.actions[]` with the expected
   effect above so Step 0 verifies the thrash rate later. If it is pure craft with no
   artifact (T1 acceptance-criteria habit), record it as a landscape teaching in
   `scorecard.levers{}` / a note — never a fake action with a metric it can't move.
5. Never grade the prompt. The retrospective measures the shape and coaches from what
   the user tells it; "your prompting is 6/10" is not a thing the plugin can or will say.

## Multiple causes

A real thrash often has two (T2 + T5: no plan, then patched forward). Name the most
upstream one first — the earlier the lever sits in the flow, the more it prevents.
Land one change, not a lecture; the next `retro` can take the second.
