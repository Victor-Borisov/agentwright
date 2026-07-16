---
description: >
  Review accumulated Claude Code friction and turn it into rules, hooks, or gates —
  then verify on later runs that the fix actually worked. Use when the user runs the
  coach, when the session-start reminder mentions pending friction signals, or when
  the user complains about recurring friction ("it keeps failing", "I always have to
  repeat this"). Follows a strict cycle: verify past fixes first, group fresh
  frictions, ask the user's judgment BEFORE showing your own, apply fixes safely,
  record for the next verification.
allowed-tools: "Bash, Read, Write, Edit"
---

# Agentwright Coach

One run = one closed loop. The order below is mandatory — especially Step 0 before
anything new: trust is built on verifying yourself before advising more.

**Dialog language.** Read `~/.claude/agentwright/config.json`; if `language` is set,
conduct the entire dialog in it. If missing, ask for the preferred dialog language as
your first question, merge the answer into the config (`{"v": 1, "language": "<answer>"}`,
create with python3 if needed, never jq), and continue in it. Artifacts (scorecard,
journal notes) stay English. Data lives in `~/.claude/agentwright/`:
`pending/pending-YYYY-MM-DD-<session>.jsonl` (friction journal, written by this
plugin's own hooks), `scorecard.json`, `flags/reviewed-YYYY-MM-DD`.

## Journal vocabulary

Each JSONL line: `{v, ts, event, project, tool?, category?, note?, effort?}`.

| event | Meaning | Role |
|---|---|---|
| `tool_failure` | A tool call failed; for Bash, `category` ∈ test/lint/build/install/git/other | friction |
| `tool_success` | A Bash call SUCCEEDED in a tracked category — the denominator for `failure_ratio` (busy day ≠ bad day) | rate denominator |
| `tool_use` | A landscape lever was used; `tool` → capability (plan_mode/subagent/worktree/mcp/web/lsp) | capability signal (credit + absence) |
| `session_start` | Session began; carries `effort` level and `pmode` (permission mode) | effort signal (O11); `pmode` → habitual `bypassPermissions` is an S3 symptom to ask about |
| `permission_denied` | Denied by the AUTO-mode classifier only — users in default mode clicking "No" produce NO event; treat absence as no-signal, not as no-denials | friction |
| `compact` | Context was compacted mid-session | friction |
| `manual` | User-authored note (via /agentwright:log) — their own words in `note` | friction, highest signal |
| `permission_request` | Permission dialog shown | rate signal: high rate = tuning friction (L4) |
| `turn` | User submitted a prompt | denominator |
| `stop` | A response cycle ended | denominator / session activity |

`session_shapes.py` turns these into `capabilities`, `failure_ratio`,
`effort_distribution`, and `unused_lever_warrants` — read those, don't re-derive.

**Always normalize per 100 turns** (`totals.friction_per_100_turns`). Raw counts lie
when activity varies, and per-SESSION rates lie worse: session count is a behavior
you yourself modify — teaching session splitting multiplies sessions and would fake
"improvement" on every open action. Session-count metrics are reserved for verifying
O1 only. Never claim improvement or regression from raw totals.

**Deterministic layer first.** Run
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/session_shapes.py` (add `--archive --days 30`
for Step 0 before/after comparisons) and work from its JSON — per-session shapes,
failure bursts, cross-session overlaps, normalized totals. Do not re-derive shapes
from raw JSONL lines.

## Step 0 — Verify past levers FIRST

Read `scorecard.json` → `actions[]` with `verified: null`. Verification is TWO-PART
(scoring.md § Verification):

- **mechanism** (deterministic, every run): the artifact is still installed and its
  proof test still blocks/fires when re-run. Set `mechanism: true/false`.
  **Read-only rule:** re-running a proof test must never itself change state. If a
  lever guards a destructive channel (SQL writes/DDL, force-push, deletes, `rm -rf`),
  confirm it by READING the guard's source/config, not by firing the destructive
  action to see if it is blocked. The plugin issues no state-changing operation
  against any target to verify anything — a guard proven by exploiting it is a guard
  the plugin just defeated on the user's real system.
- **outcome** (statistical, graded strong/weak/none): requires ≥5 friction EVENTS of
  the matching category pre-period, a post-window at least as long as the pre-window,
  and the post rate (per 100 turns) below the **pre-spike baseline** — never below
  the spike that triggered the fix; spikes fall by regression to the mean regardless
  of the lever. Do not eyeball two small numbers into a verdict.

Verdicts: mechanism+strong → `verified: true` (full F1 credit) · mechanism-only after
the event floor is unmet for 4 weeks or 20 active sessions → `verified: true` with
the note "insufficient traffic; mechanism confirmed, friction has not recurred"
(half F1 credit) · mechanism false or outcome regressed → `verified: false`, propose
rework or rollback (escalate the guarantee ladder: rule → hook → gate), and name
factually what the approval missed if the artifact was defective · otherwise leave
`null` and say exactly which floor is unmet (events or window).

## Step 1 — Group fresh frictions by root cause

Read all `pending/*.jsonl` files from BEFORE today. Cluster by category + project +
recurrence — three irritations are often one hole ("no automatic verification
loop"). Treat `manual` notes as anchors: they say what the user actually felt; quote
them verbatim when presenting the group. A high `permission_request` rate (roughly
>5 per session) is itself a friction group even with zero denials. Prioritize:
HIGH-cost and frequent first. If the journal has no friction events, say so briefly
and stop — no noise.

A group whose friction already has an OPEN action in `scorecard.actions[]`
(`verified: null`) is presented as "in verification — waiting for signal", never
re-asked or re-treated. This also makes interrupted runs safe: if a previous cycle
was abandoned after applying a fix, the next run recognizes the treated friction
instead of proposing the same lever twice.

A group whose only fix is blocked on someone else and already sits in
`scorecard.blocked_external[]` (scoring.md § Growth vs blocked-on-others) is NOT
re-raised. Do not propose "remind them again" as a lever — escalation was the mature
action and it is done. Mention it once as status if relevant ("still blocked on the
DBA login") and move on; it re-enters only if the user says the blocker cleared or
changed.

**Attribution before treatment.** Failure counts conflate three different things.
For each new group ask ONE attribution question — "agent's mistake, environment
(flaky infra, missing deps), or you deliberately iterating (red-green TDD)?" — and
record the answer in the group. Environment noise gets an environment fix or nothing;
deliberate iteration is NOT friction (do not propose a lever against the user's own
workflow); only agent-caused recurrence proceeds to Steps 2–4. Step 0 must compare
like with like: verify against the same attribution class the action was created for.

## Step 1b — Nominate missed opportunities (session shapes)

Pain detectors only catch what hurts; this step catches what silently costs. Match
the session shapes against `${CLAUDE_PLUGIN_ROOT}/references/opportunities.md`
(long multi-wave sessions WITH a compaction → session splitting; overlapping
sessions in one project → worktrees; huge-turn sessions → subagents; failure bursts
→ rewind; recurring themes → a skill; large session without plan mode → plan mode;
uniform effort across mixed tasks → effort tuning; configured-but-unused MCP).

**Use the precomputed signals.** `session_shapes.py` now emits `unused_lever_warrants`
(warrant + absence, already checked against the `capabilities` map), `failure_ratio`
(a category with high failures BUT high successes is a busy day, not a broken lever —
weight nominations by ratio, not raw failure count), `friction_confidence` (per-category
grade), `effort_distribution`, and `capabilities` (what the user demonstrably used).

**Confidence pacing** (scoring.md § Confidence grading). Every warrant, thrash entry,
and friction category carries a grade. Order nominations **strong → medium**, at most
1–2/run; **never nominate a `weak` finding as a problem** — it graduates to medium when
it recurs. UPGRADE one tier when a `/log` note in the user's words names the same
theme. And apply CONTRADICTION: if the user's own claim is directly negated by the
journal — "tests always fail" but `failure_ratio[test].ratio < 0.3`, or "I always use
plan mode" but `capabilities.plan_mode.used == false` — do NOT nominate or agree;
surface the conflict, ask which sessions they mean, record nothing until it clears. A warrant fires only when the lever
was NOT used — never nominate a lever `capabilities` shows in active use; instead note
it as confirmed landscape for the next `/score`.

**Thrash → point to `/retro`.** If `thrash_sessions` is non-empty, a session went in
circles (burst, or a large session with a category stuck at a high failure ratio).
Do NOT try to diagnose the cause here from metadata — the cause lives in what the user
did, which needs their account. Surface it once and hand off: "Session X looks like it
looped (a 4-failure test burst, ratio 0.83). Want to run `/agentwright:retro` on it? —
it finds the upstream fix from what you tell it, without reading your prompts." The
retrospective owns that flow (`references/thrash.md`); the coach only flags it.

Hard rules: **nominate, never convict** (show the evidence, ask); **at most 1–2 candidates per run**; **check
`scorecard.opportunities[]` first** — a `dismissed` entry is re-asked only when its
recorded dismissal REASON is invalidated by new evidence (not by raw amplitude);
every asked candidate gets recorded as `adopted` / `taught` / `dismissed`
(`dismissed` counts as *known* for scoring — full refusal credit is minted only in
the score dialog). The question always carries the mini-lesson (what the lever
guarantees, what it costs) — this is where landscape teaching happens, at the moment
of a real situation.

**No friction? Teach anyway.** Update the `scorecard.levers{}` coverage map
(never_discussed / taught / adopted / dismissed) every run. When a run has no
friction groups and no shape nominations, spend the nomination budget on the
highest-value `never_discussed` lever, framed against the user's real (clean)
session data: "your sessions are clean — here's a lever you've never had a reason to
meet." A disciplined user must not be locked out of the landscape by their own
discipline. For levers `taught` more than ~2 weeks ago and still not adopted, ask
one retention check ("we covered worktrees — here's last Tuesday's overlap; what
applies?") before teaching anything new.

## Step 2 — Ask the user's judgment BEFORE showing yours

Per friction group: "What would you reach for here — rule in CLAUDE.md, hook, CI gate,
MCP, nothing? Why?" Wait for the answer. This is the judgment-training moment; never
lead the witness.

**Mastery model — the ritual must not decay into a captcha.** Track consecutive
correct picks per lever class in `scorecard.mastery{}`. After 3 consecutive correct
picks in a class, SKIP the question for that class ("hook again — applying, say if
you disagree") and instead spot-check occasionally (~every 4th occurrence) — that IS
spaced repetition. A wrong spot-check answer resets the counter and the question
returns. Forcing a fluent user to re-answer the same question is friction from a
friction-reduction tool, and throwaway answers would corrupt the judgment signal.

## Step 3 — Show your pick, compare

Give your lever with a consequences-based justification (what it guarantees, what it
costs — use the guarantee ladder from `${CLAUDE_PLUGIN_ROOT}/references/levers.md`).
Highlight the divergence: where you agree, where not, whose fits this context better
and why. A divergence is teaching material, not a verdict. If the user systematically
never considers some lever class, point at the blind spot: "third time a rule where a
guarantee is needed — there is a lever you haven't tried."

## Step 4 — Apply the agreed fix, safely

- Match the friction against `${CLAUDE_PLUGIN_ROOT}/references/levers.md` and start
  from the recipe (it includes the artifact template, the proof test, and the
  expected-effect metric). Improvise only when no recipe fits, and say you are.
- **HIGH-cost** (hook, permissions, MCP config, CI gate — anything embedded in the
  harness or touching security): run the recipe's **proof test** before applying
  (e.g. feed the hook a failing case and assert the blocking exit code), show the
  artifact and the test result, get an explicit review from the user.
- **CHEAP** (a CLAUDE.md line, a one-off tweak): apply without ceremony.
- If in a git repo, put the change in its own commit so rollback is one command; if
  not, back up the file being modified first.
- Record in `scorecard.json` → `actions[]`: friction, lever, date, `expected` (the
  recipe's normalized metric, e.g. "tool_failure/test rate per 100 turns drops
  in project X"), `verified: null`. Record **immediately after each individual
  fix** — never batch records for the end of the run. An applied artifact without
  a scorecard entry is an orphan: Step 0 will never verify it, and the next run
  will re-propose a fix for friction that is already treated.

## Step 5 — Close the day

- Archive processed pending files: move them into `~/.claude/agentwright/archive/`
  (create if needed). Never delete unprocessed ones.
- Touch the flag: `~/.claude/agentwright/flags/reviewed-$(date +%F)`.
- One-line summary: N frictions reviewed, M levers applied, K past actions verified.
- If judgments in Step 2/3 revealed a landscape gap, end with ONE pointed Anthropic
  Academy module recommendation tied to that exact gap — no course dumps.

## When invoked from a passing complaint

If this skill triggered because the user complained in conversation (not via the
command), first log the complaint as a `manual` journal entry through
`bash ${CLAUDE_PLUGIN_ROOT}/scripts/log-friction.sh "<one factual English sentence>"`,
tell the user it was logged, and ask whether they want the full review now or at the
next scheduled one. Do not force the whole cycle on someone mid-task.

## Privacy rails (hard rules)

- Work only with this plugin's own journal, git state, and config artifacts.
- Never read `~/.claude/projects/` (transcripts) or `~/.claude/usage-data/`.
- Never send anything anywhere; everything is local.
