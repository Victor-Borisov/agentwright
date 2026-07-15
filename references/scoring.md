# Agentwright Score — computation rules

The score is a single number 1–100. You compete only with yourself: the report always
shows the delta vs the previous run and why it moved. The number must be reproducible:
same facts + same answers → same score — and the stickiness rules below are what
enforce that, not the aspiration.

## Weights

| Item class | Weight |
|---|---|
| S1–S5 (security) | 2.0 each |
| HIGH-cost items (B1–B3, E1–E2) | 1.5 each |
| CHEAP items (A*, C*, D*) | 1.0 each |
| F1–F2 (effect) | 2.0 each (only when assessed) |

## Formula

```
raw   = Σ (credit_i × weight_i)          over all items NOT not_assessed
denom = Σ (weight_i)                     over the same items
score = round(100 × raw / denom)
```

Credits: `present` = 1.0 · `conscious_refusal` = 1.0 · `partial` = 0.5 · `absent` = 0.0.

**Precision band.** The score is reported with an explicit band: ± half the share of
dialog-derived weight, floored at ±2 (e.g. "72 ±3"). A level label never changes on a
delta smaller than the band unless a named fact changed (new artifact, gate event,
verified action).

## Reproducibility — status stickiness

Previous `items[]` in the scorecard are the PRIOR, not a suggestion:

1. Re-adjudicate an item ONLY if its underlying facts changed (scan diff vs the
   recorded evidence) or the user volunteers a new answer in the dialog.
2. A judgment **downgrade on unchanged facts** is an *adjudication change*, not a user
   regression: apply it, but flag it in the report ("re-read stricter — not counted
   against you") and exclude it from the "what you lost" narrative.
3. Refusal reasons are persisted (`items[].reason`) and carried forward; re-validate a
   reason only when the journal contradicts it (see below).

## Conscious refusal — the quality bar is enforced, not decorative

`conscious_refusal` earns full credit ONLY when all three hold:

1. The user names the lever AND its tradeoff AND a context-specific reason
   (checklist.md quality bar).
2. **Journal consistency:** the refusal is not contradicted by observed friction of
   the matching category. Refusing a test loop (B2) while `tool_failure/test`
   friction is present in the journal caps the item at `partial` and MUST be
   challenged: "you refuse the lever, but the pain it removes is in your data."
3. The reason survives re-validation: if the contradicting signal appears later, the
   next run re-opens the item instead of silently keeping the credit.

**Coach dismissals do NOT mint refusal credit.** A `dismissed` opportunity records
status `taught` semantics for scoring: the lever is known. Full refusal credit is
granted only in the score dialog under the bar above. (Rationale: the coach's
dismissal bar — one sentence to a nomination — is lower than the score bar, and the
laundering path would otherwise be the easiest way to inflate the number.)

## Security gate (applied after the formula)

The caps are NOT arbitrary constants — they are level boundaries minus one, so the
gate speaks the language of the levels. If the level bands ever change, the caps
move with them.

**Two questions before any cap applies** (added v3 — a cap punishes a person, so it
must key on what the person controls and what they already did):

1. **Whose finding is it?** A risk that lives in the environment the user cannot
   change — an over-privileged shared DB login, an inherited legacy secret, a
   team-owned `.gitignore` — caps the PROJECT readiness score, NOT the user score.
   The user score is capped only by a hole in user-level config or user-authored
   artifacts. (This is the same user-vs-project rule as below, applied to the gate.)
2. **Did they mitigate?** A guard the user built that is present but imperfect
   (a validator with a bypass, a deny-list with a gap) is graded `partial` on
   credit — but a built-and-imperfect guard is *more* mature than none, so it does
   NOT drag the user score below the Architect line while the residual risk is
   environmental. Capping a guard-builder below a build-nothing user is a perverse
   incentive and is forbidden.

With those settled, the caps:

- Any **user-controllable** S item `absent` with a live finding (real secret,
  `allow:["*"]`, bypassPermissions as default) → score = min(score, **59**) — one
  below Agent Builder: *with a live security hole you cannot even be a Builder.*
- Any **user-controllable, unmitigated** S item `partial` → score = min(score,
  **84**) — one below Agent Architect: *a solid Builder, but not an Architect with
  half-closed security.* A `partial` whose residual risk is environmental caps the
  PROJECT score only.
- Any S item `not_assessed` (probe unavailable) → also min(score, **84**):
  *unverified security cannot be Architect either.* This keeps installing better
  probes (gitleaks) from ever lowering a score relative to not installing them.
- The report must name the capping item, say whether it capped the user or a
  project, and place "Step 0: Hardening" first in the plan.

**Verification is read-only — always.** Establishing whether a guard holds is done
by READING the artifact (MCP source, deny-list, hook, config), never by executing
an exploit. The plugin must never issue a state-changing action — no writes, DDL,
force-push, deletes, or destructive shell — against any target, on any tier, to
"prove" a finding. A bypass is demonstrated by reading the code path, not by driving
it. (An assessment tool that writes to a user's database has itself failed the
oversight axis it measures.)

## Levels

| Score | Level |
|---|---|
| 85–100 | **Agent Architect** |
| 60–84 | Agent Builder |
| 1–59 | Agent Apprentice |

Levels exist only as milestones for the self-race; no percentiles, no comparison with
others in this local version.

## Normalization — one rule for every rate

All friction rates compare **per 100 turns** (`totals.friction_per_100_turns` from
`session_shapes.py`). Never per session: session count is a behavior the coach itself
modifies (teaching session splitting multiplies sessions and would fake improvement
across every open action). Session-count metrics are reserved for verifying O1 itself.

## Verification of actions (feeds F1) — two-part, with expiry

Each `actions[]` entry is verified on two independent tracks:

- **mechanism** (deterministic, no statistics): the artifact is still installed AND
  its proof test still blocks/fires when re-run. Checkable on every coach run.
- **outcome** (statistical, graded `strong` / `weak` / `none`): requires ≥5 friction
  EVENTS of the matching category in the pre-period, a post-window at least as long
  as the pre-window, and the post rate below the **pre-spike baseline** (the rate
  before the spike that triggered the fix — never below the spike itself, which
  falls by regression to the mean regardless of the lever).

F1 credit: full for mechanism + `strong` outcome; half for mechanism-only.
**Expiry:** if after 4 weeks or 20 active sessions the event floor is still unmet,
downgrade to mechanism-only verification with the non-event criterion ("friction has
not recurred") and say explicitly: "insufficient traffic to measure outcome;
mechanism confirmed." An `actions[]` entry never stays `null` forever.

F2 (friction trend) EXCLUDES `manual` events — they measure the user's attentiveness,
and counting them would penalize the diligent logger. A logged-then-resolved note is
a positive signal, not friction.

## Anti-gaming rules

1. A freshly created empty artifact (e.g. a skill added minutes before scoring) counts
   `partial` at best. `present` = existence + authorship history (git log / file
   mtimes — checkable facts), NOT claimed usage: invocation counts are not observable,
   so the rules never pretend to check them.
2. `conscious_refusal` requires the full bar above, including journal consistency.
   When in doubt, score `partial` and say why.
3. F items can push the score DOWN between runs (a lever that didn't work, friction
   that grew). A falling score with a named cause is a feature, not a bug.
4. Never round up to cross a level boundary. 84.4 is 84.

## User score vs project readiness

The headline **Agentwright Score is a user-harness score**: user-level artifacts
(user settings, user CLAUDE.md, skills), all D/E dialog items, and verified F effects.
Project-scoped items (S1–S2 repo findings, A1, B2–B3, C project artifacts) form a
**per-project readiness score**, keyed by project in the scorecard. When the scan
ran in workspace mode (a non-repo root containing repos), each repo gets its own
`project_scores{}` entry keyed by repo name; the root itself is never scored — a
workspace root is a layout, not a project, and "not a repo" is not "unverified".

**S2 has two readings** (`repo.env_ignore`): for the USER score, effective coverage
from ANY source counts in full — a `local_exclude` or `global` ignore proves this
user cannot leak secrets from this machine, and personal protection is often the
only lever available to a developer without commit rights to `.gitignore`. For
PROJECT readiness, only `committed` coverage counts in full: an ignore that lives
on one machine does not protect the rest of the team, so the project cap stands,
reported as "covered on this machine; team-level `.gitignore` still missing" — and
the pending team fix, once the user has raised it, is a blocked-on-others item (see
below), not a personal growth item. The security gate
always caps the project score; it caps the USER score only when the finding lives in
user-level config or user-authored artifacts. (Rationale: an inherited legacy repo's
old secret describes the repo's past, not the user's maturity — and a certifiable
number must not whiplash between repos.) The report shows both: "You: 74 ±3 · This
project: 61 (capped by S1)."

**S5 has the same split** (`destructive-command guard`): the shell deny-list and any
self-authored guard (e.g. an MCP SQL validator) are user artifacts — a gap the user
can fix is a user-level `partial`. But when the destructive *power* comes from the
environment (a DB login granted `db_owner`/`sa` by a DBA the user cannot overrule),
that privilege is a project/environment fact: it caps project readiness, while the
user keeps full credit for having built a guard at all. Report it as "guard present
but bypassable (your MCP — fixable); underlying DB privilege is environmental
(escalate to DBA)". Step 0 lists the layer the user CAN do (fix the validator); the
DBA layer, once raised, is blocked-on-others, not a repeated to-do.

## Growth vs blocked-on-others

A growth item is something the user can close **by their own hand**: a lever to learn,
a config or artifact to change, a task in their own repo. A gap whose only remaining
action belongs to someone else — a DBA must grant a role, a lead must approve a
team-owned file, a ticket the user is not allowed to open — is NOT a growth item and
must never be presented as one. A plan that tells the user to "grow" by asking a
colleague a third time has stopped measuring the user and started measuring the
colleague; that is a defect.

Escalation is the terminal mature action for such a blocker. Once the user has raised
it (to a lead, a DBA, a ticket queue — or reports they are structurally unable to),
that credit is earned and fixed; a second or third reminder is not a higher level.
Record it in `blocked_external[]` and never re-ask or re-list it. It caps project
readiness only (the risk is real for the repo), never the user, and re-surfaces only
if the owner acts or the user says the situation changed. When every remaining cap is
a blocked-on-others item, the correct growth section is: "no personal gaps right now;
the rest is organizational and already escalated" — a strong result, not a void to pad.

## Scorecard persistence

Write `~/.claude/agentwright/scorecard.json` after every scoring run:

```json
{
  "version": 1,
  "checklist_version": 1,
  "date": "2026-07-02",
  "score": 72,
  "score_band": 3,
  "level": "Agent Builder",
  "cap_applied": null,
  "project_scores": {"shop-api": {"score": 61, "cap_applied": "S1", "date": "2026-07-02"}},
  "axes": {"landscape": 0.8, "judgment": 0.7, "oversight": 0.6, "outcome": 0.75},
  "items": [
    {"id": "S3", "status": "present", "evidence": "deny list: 14 rules, mode=auto"},
    {"id": "D2", "status": "conscious_refusal", "reason": "solo scripts repo, plans add ceremony"}
  ],
  "actions": [
    {"friction": "test failures repeat across sessions", "lever": "L1 PostToolUse test hook",
     "date": "2026-07-02", "expected": "tool_failure/test rate per 100 turns drops in shop-api",
     "verified": null, "mechanism": null, "outcome": null}
  ],
  "opportunities": [
    {"id": "O1-session-splitting", "status": "dismissed", "date": "2026-07-03",
     "note": "single long-running research task; waves are lunch breaks"}
  ],
  "blocked_external": [
    {"item": "S5-db-privilege", "action": "read-only DB login (db_datareader + scoped GRANT EXECUTE)",
     "owner": "DBA / team lead", "escalated_on": "2026-07-01", "reminded_on": "2026-07-08",
     "status": "awaiting"}
  ],
  "levers": {"L1": "adopted", "L4": "taught", "O2": "never_discussed"},
  "mastery": {"guarantee-levers": 3},
  "history": [{"date": "2026-07-02", "score": 72, "checklist_version": 1,
               "project": "shop-api",
               "axes": {"landscape": 0.8, "judgment": 0.7, "oversight": 0.6, "outcome": 0.75}}]
}
```

- `actions[]` is the contract for the coach's Step 0 (two-part verification above).
- `opportunities[]` is the contract for Step 1b: `adopted` / `taught` / `dismissed`.
  For scoring, `dismissed` = the lever is known (`taught`); refusal credit is minted
  only in the score dialog.
- `blocked_external[]` records gaps the user has escalated but cannot close
  themselves (see § Growth vs blocked-on-others). Once here, an item is never a growth
  item and is never re-asked; it caps project readiness only, and clears when the owner
  acts or the user reports a change. Preserve it across runs like `actions[]`.
- `levers{}` is the coverage map (never_discussed / taught / adopted / dismissed) —
  it drives what the coach teaches when there is no friction (see coach Step 1b).
- `mastery{}` counts consecutive correct Step-2 picks per lever class — it drives
  when the judgment ritual is skipped and spot-checked instead.
- `history[]` entries carry `axes` and `project` so long-term trends can be reported
  per axis ("oversight flat for 3 months") and segmented by project.

## Evolution contract — when the measured set itself changes

The self-race promise must survive two kinds of set changes:

**(a) Checklist version grew** (`checklist_version` differs from current
`knowledge_version`):

1. Compute the score twice: over the OLD item set (comparable delta — "your
   changes") and over the full new set (the new official score).
2. Attribute the difference explicitly: "the bar moved: −3, because N new
   capabilities entered the checklist" — named items, each a growth direction,
   never a penalty.
3. New items enter softly: `(new in vN)` items score normally, but an `absent` on
   them appears under "the bar moved", not "what you lost".

**(b) F items entered** (first run excluded F1–F2; the second run includes them —
within the same checklist version): apply the IDENTICAL two-score computation —
comparable delta over the run-1 item set, official score over the full set, gap
labeled "effect items now measurable". The first delta a user ever sees must be the
best-explained one, not the worst.

In both cases append to `history[]` with the new official score and the
`checklist_version` alongside.

Staleness: if the facts JSON reports the running Claude Code major.minor is ahead
of `calibrated_for_claude_code`, say so in the report header: the checklist may be
missing recently added capabilities, so the score is a floor of the landscape, not
the ceiling — and suggest updating the plugin.
