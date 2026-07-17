# Agentwright backlog

The living tracker of everything worth improving. Sourced from the 2026-07-06
three-critic review (technical / methodology / consistency) and updated as work lands.
Format: `[ ]` open · `[x]` done (with version) · `[~]` partial. Severity in brackets.

Run the review again after any major version — critics find new things once old ones
are fixed.

---

## Done in v0.4.0 (2026-07-06 review response)

### Technical (would not work / silent wrongness)
- [x] **[BLOCKER] Version capture was dead code** — SessionStart stdin has no `version`
  field (that's statusline-only). `session-start.sh` now shells `claude --version` in
  the background, cached once/day; the whole staleness→calibration→banner chain was
  dependent on this.
- [x] **[BLOCKER] S4/C3 read a nonexistent file** — user-scope MCP lives in
  `~/.claude.json`, not `~/.claude/.mcp.json`. `scan_artifacts.py` now parses
  `~/.claude.json` (top-level + per-project `mcpServers`); the security probe actually
  probes now.
- [x] **[BLOCKER] `${CLAUDE_PLUGIN_ROOT}` in `allowed-tools` frontmatter is undocumented**
  — likely never matched → permission prompt on every score/log run. Switched score/log
  skills to plain `Bash` (as coach already did).
- [x] **[BLOCKER] Manual-note pseudo-session corrupted the deterministic layer** —
  `pending-<date>-manual.jsonl` became a day-spanning fake session, fabricating O2
  worktree nominations and skewing totals. `session_shapes.py` now keys on the session
  SUFFIX (midnight-safe), treats `manual` as a separate notes stream, excludes it from
  session count / overlaps / waves.
- [x] **[MAJOR] Env-var payload cap (E2BIG)** — big `tool_response`/prompt dropped the
  event. Rewrote collector as `collect_friction.py` reading stdin; `.sh` is a thin pipe.
- [x] **[MAJOR] `grep -c || echo 0` produced `"0\n0"`** and an integer-expr error →
  fixed with `n=${n%%[!0-9]*}`.
- [x] **[MAJOR] Unquoted `${CLAUDE_PLUGIN_ROOT}` in hooks.json** — space in plugin path
  broke every hook. Now `"${CLAUDE_PLUGIN_ROOT}"`-quoted.
- [x] **[MAJOR] `python3` not found on Windows Git Bash** silently no-op'd everything;
  `/log` claimed success while writing nothing. Now falls back `python3 || python`, and
  `log-friction.sh` emits an error + non-zero so the skill can't confirm a phantom write.
- [x] **[MINOR] `dict | dict` (3.9+)** → `{**a, **b}` for 3.8 compat.
- [x] **[MINOR] Unbounded fallback secrets scan** — added 5000-file cap + more skip dirs
  (`dist`/`build`/`target`/…) + `truncated` flag; gitleaks path no longer uses
  `/dev/stdout` (tempfile instead).
- [x] **[MINOR] `plugins` counted marketplace clones** → parse `installed_plugins.json`.
- [x] **[MINOR] Nested skills/commands undercounted** → recursive glob.
- [x] **[MINOR] UTC ts vs local-date filename** → both local now (`%z` offset stamps;
  `session_shapes.py` still parses legacy `Z`).
- [x] **[MINOR] Shell-injection surface in `/log`** → single-quote instruction + strip.
- [x] **[MINOR] `__pycache__` / critic test artifact** removed.

### Methodology (score defensibility / develops)
- [x] **[MAJOR] Conscious-refusal cheat code** — refusal now requires journal
  consistency (a refusal contradicted by observed friction of that category caps at
  `partial` and is challenged); coach dismissals no longer mint refusal credit (only the
  score dialog does, under the full bar).
- [x] **[MAJOR] Run-to-run variance** — status stickiness: re-adjudicate only on changed
  facts; a stricter re-read of unchanged facts is an "adjudication change," flagged and
  excluded from "what you lost." Score reported with a ± precision band.
- [x] **[MAJOR] Step-0 regression-to-the-mean** — verification is now two-part:
  mechanism (deterministic) + outcome (graded, ≥5 events, post-window ≥ pre-window,
  compared to pre-SPIKE baseline). F1 full for mechanism+strong, half for mechanism-only.
- [x] **[MAJOR] Per-session normalization confound** — switched every rate to
  **per 100 turns** (turn count is stationary; session count is a thing the coach itself
  changes). Session metrics reserved for verifying O1 only.
- [x] **[MAJOR] Failure ≠ friction attribution** — coach Step 1 now asks one attribution
  question per group (agent / environment / deliberate TDD iteration); only agent-caused
  recurrence proceeds; Step 0 compares like with like.
- [x] **[MAJOR] First-run→second-run incomparability** — the two-score evolution
  contract now also fires at F-entry ("effect items now measurable").
- [x] **[MAJOR] Rare-friction verification deadlock** — expiry: after 4 weeks / 20
  sessions unmet, downgrade to mechanism-only with the non-event criterion.
- [x] **[MAJOR] O1 fires on every lunch break** — compaction is now a MANDATORY conjunct;
  dismissal re-ask keys on the recorded REASON being invalidated, not on amplitude.
- [x] **[MAJOR] Landscape never completes for clean users** — `scorecard.levers{}`
  coverage map; a no-friction coach run teaches the highest-value never-discussed lever.
- [x] **[MAJOR] Step-2 captcha decay** — `scorecard.mastery{}` counter; after 3 correct
  picks in a class the question is skipped + spot-checked (spaced repetition).
- [x] **[MAJOR] User vs repo conflation** — headline = user-harness score; project items
  form a per-project readiness score (`project_scores{}`); the gate caps the user score
  only for user-level findings. Inherited legacy secrets no longer cap the user.
- [x] **[MINOR] Diligent logger penalized by F2** — F2 trend excludes `manual` events.
- [x] **[MINOR] `present` "in use" unenforceable** — redefined as existence + authorship
  history (git/mtime); dropped the usage claim.
- [x] **[MINOR] gitleaks-absent lowers score** — `not_assessed` on S items now also caps
  at 84, so better probes never hurt.
- [x] **[MINOR] Per-axis trend + first-run mode** — `history[].axes` stored & reported;
  first `/score` limited to core items.

### Consistency
- [x] Simulator "one/two per section" claim (C/E/F unshown) — reworded, both langs.
- [x] "four statuses" → names four + not_assessed.
- [x] Simulator S1 `partial` text described S2's probe — fixed.
- [x] README failure-category list missing `other` + Bash-only scope — fixed.
- [x] MAINTAINING "Phase A node" (nonexistent) → `#day` flow; RU docs added to sync lists.
- [x] refresh skill knowledge_version/minor-bump conditions aligned with the contract.
- [x] README data-dir list (added archive/state).
- [x] RU walkthrough tab labels restored; "5-hour"→"7-hour" example everywhere.

---

## Done in v0.4.1 (first field bug, 2026-07-13)

- [x] **[BLOCKER] Scripts shipped without the executable bit** — the repo lives on a
  Windows mount where git records mode 100644, so every hook died with
  "Permission denied" (126) on install. Two-part fix: `git update-index --chmod=+x`
  on all `.sh`, AND every invocation (hooks.json, skills, statusline docs) now goes
  through an explicit `bash`/`python3` so the plugin never depends on the exec bit
  again. Guard added to the MAINTAINING test suite.

## Done in v0.4.2 (dogfood findings, 2026-07-14)

- [x] **[MAJOR] Dialog language was implicit** — "respond in the user's language" gave
  English for bare `/score` invocations. Now `~/.claude/agentwright/config.json` holds
  `language`; score/coach ask once on first run (their first question) and persist it;
  log obeys but never asks (stays instant). Artifacts remain English.

## Done in v0.5.0 (workspace mode — field find, 2026-07-14)

- [x] **[MAJOR] Scanner assumed cwd == one git repo** — a workspace root holding
  several clones side by side (plus personal non-git dirs) scanned as "not a repo →
  S2 unverified → project capped 84" even with every real repo
  covered. Now: when cwd has no `.git`, `workspace_facts()` scans every immediate
  subdir that IS a repo (gitignore coverage, CI, secrets, per-repo CLAUDE.md; cap 20,
  `truncated` flag), score writes one `project_scores{}` entry per repo and never
  scores the root; personal non-git dirs are listed by name only and never scanned.
- [x] **[MINOR] CI detection was GitHub-only** — `.gitlab-ci.yml` now probed
  (`repo.gitlab_ci`), in both single-repo and workspace modes.

## Done in v0.6.0 (show command + integrity seal, 2026-07-14)

- [x] **[MAJOR] No way to display the score without recomputing** (field ask: screen-
  sharing a level in a call). New read-only `show` skill: seal check → render card
  (headline ± band, axes, per-project, trend, mandatory self-assessed disclaimer),
  never recomputes, never asks.
- [x] **[MAJOR] Scorecard trivially editable before showing** — `card_integrity.py`
  stamp/check: sha256(install salt + canonical card), stamped by score on every
  write; show REFUSES to render a mismatched card. Disclosed limit: tamper-evidence
  against casual edits only — a determined user can re-stamp (open source, local
  salt); real third-party verification requires an external signing service, out of
  scope for the local plugin.

## Done in v0.7.0 (S2 without commit rights — field find, 2026-07-14)

- [x] **[MAJOR] S2 was blind to personal ignore protection** — a developer without
  commit rights to the team `.gitignore` (common in company repos) had no way to
  clear S2, even with `.git/info/exclude` or a global `core.excludesFile` fully
  covering secrets. Scanner now asks git itself (`git check-ignore -v`) and reports
  `env_ignore: {effective, sources: committed|local_exclude|global}`; scoring split:
  effective coverage (any source) clears the USER, committed coverage required for
  PROJECT readiness — local-only coverage renames the cap to "covered on this
  machine; team-level fix pending".

## Done in v0.8.0 (security-gate fairness + read-only verification — field find, 2026-07-14)

- [x] **[BLOCKER] Verification executed a live write to prove a finding** — a score run
  ran `create table #probe; insert; select` against a production DB via a self-authored
  MCP to demonstrate the SQL validator was bypassable. Temp table = no real damage, but
  an assessment tool must NEVER issue a state-changing action. New hard rule (scoring.md,
  checklist S-gate, score + coach skills, MAINTAINING privacy lines): guards are verified
  by READING the artifact/code path, never by driving the destructive action. No write/
  DDL/delete/force-push/destructive-shell against any target on any tier, ever.
- [x] **[MAJOR] Security gate punished guard-builders and environmental risk as if
  user faults** — a `partial` on ANY S item capped the user at 84, so a user with a
  powerful capability + an imperfect self-built guard scored WORSE than a user with no
  capability at all, and an environmental privilege (DB `db_owner` the user cannot
  change) capped the USER not the project. Gate now asks two questions first (whose
  finding / did they mitigate): environmental risk caps PROJECT only; a built-but-
  imperfect guard never drags the user below Architect while residual risk is
  environmental. S5 rescoped like S2 (user artifacts cap user; DB privilege caps
  project). knowledge_version 2 → 3.

## Done in v0.8.1 (staying current, 2026-07-14)

- [x] **[MINOR] No update discovery for end users** — updates are pull-based and
  auto-update is OFF by default for third-party marketplaces. Documented the one-time
  auto-update toggle (`/plugin` → Marketplaces → Enable auto-update) in README + both
  docs; noted the real hands-off path is the official `claude-community` catalog (CI
  bumps the pin, auto-update default-on). session-start.sh now prints a one-time
  "updated to vX — what changed" line after a genuine version change (detected via
  plugin.json version vs a `state/plugin-version` marker; first run writes it
  silently). Deliberately NOT built: an "upstream has a newer version" nudge — that
  needs a network call, which the plugin forbids; the limit is stated plainly in the script.

## Done in v0.8.2 (growth ≠ nagging — field find, 2026-07-14)

- [x] **[MAJOR] Growth plan listed blockers the user cannot action** — repos capped by
  an environmental S2/S5 gap (team `.gitignore`, DBA-granted DB privilege) surfaced the
  fix as the user's "growth item" every run, so a user who had already escalated twice
  was told to "grow" by nagging a lead a third time. A plan that measures the
  colleague, not the user, is a defect. Fix: growth items are USER-ACTIONABLE ONLY;
  a gap whose only remaining action belongs to someone else goes to a new
  `scorecard.blocked_external[]` (item/action/owner/escalated_on/reminded_on/status),
  is credited as the terminal mature action (escalation done), never re-asked, never
  re-listed as growth, caps project readiness only. Zero user-actionable items is now
  an explicit valid result ("no personal gaps; the rest is organizational and already
  escalated"). Coach Step 1b also refuses to re-raise a blocked_external item. No
  credit/cap math changed → knowledge_version stays 3 (presentation + re-nag behavior
  only).

## Done in v0.9.0 (widen the aperture — detectors from more hook events, 2026-07-15)

Step 0 (non-negotiable) verified the hook API on current CC BEFORE building: `model`
is NOT in any hook payload (only the transcript, which is off-limits) — so
model-per-task stays dialog-only; `effort.level` IS in the payload, `tool_name` is in
every tool hook. Built on facts, not the guessed `model` field.

- [x] **[MAJOR] Log tool successes per category** — now collected via `PostToolUse`
  (matcher `Bash`, event `tool_success`); `other`-category successes dropped as noise.
  `session_shapes.py` + `scan_artifacts.py` emit `failure_ratio` per category, so a
  busy productive day (high failures AND high successes) is no longer read as a bad one.
- [x] **[MAJOR] Dialog-only levers made observable** — subscribed to `PostToolUse` for
  the landscape tools (EnterPlanMode/ExitPlanMode, Task/Agent, EnterWorktree, mcp__*,
  WebSearch/WebFetch, LSP) → journal `capabilities_used`; plan mode (O10), subagent
  (O3), worktree (O2), MCP-use, effort-per-task (O11, from `effort.level`) are now
  detected, not just asked. New "warrant + absence" detector shape
  (`unused_lever_warrants`): a lever is nominated only when a situation warranted it
  AND `capabilities` shows it unused. Positive side: observed use CREDITS landscape in
  `/score` without asking and skips the mastery captcha. New O12: configured-but-unused
  MCP. knowledge_version 3 → 4; D2/D4/D5/D6 rows gained signals.
- [x] Privacy: MCP tool names collapse to `mcp` (server names are private infra);
  effort level added to the declared journal schema in README + both docs.
- [x] `permission_mode` captured at `session_start` (free payload field, like effort) →
  `pmode_levels`/`pmode_distribution`; habitual `bypassPermissions` is an OBSERVED S3
  symptom the coach asks about (may be a conscious isolated-container choice → refusal,
  not a finding). Deliberately NOT built into signals: review commands (`/code-review`,
  `/security-review`) and launch modes (`-p`, `--output-format`, CI) — their absence is
  not friction-with-a-trace (bugs surface in CI/prod, not our journal); they stay
  dialog/artifact-scan. Those dashes are correct, not gaps.
- [x] Cost/safety: only non-blocking `PostToolUse`/`SessionStart` hooks added; the one
  high-volume hook (Bash success) is documented as removable; no blocking hook used for
  logging. Known limit: worktree/subagent started via a CLI flag (not the in-session
  tool) leaves no `tool_use` trace — acceptable, coaching cares about in-session use.

## Done in v0.10.0 (help with thrashing without reading prompts, 2026-07-15)

Addresses the deepest known gap — prompt/approach quality is unmeasurable by policy
(§1.F, no transcript access) — WITHOUT faking a proxy. The plugin can't read prompts,
but "going in circles" leaves a SHAPE it can see (`failure_ratio` from v0.9.0 separates
stuck from busy).

- [x] **[MAJOR] Thrash detection + stuck retrospective** — `session_shapes.py` emits
  `thrash_sessions` (a failure burst, OR a large session with a category stuck at
  ratio ≥ 0.6 with ≥ 3 failures; compaction strengthens, never triggers alone). New
  `/agentwright:retro` skill: reflects the SHAPE non-judgmentally, asks ONE open
  question ("what were you doing, where did it loop?"), takes the user's judgment
  first, maps their account to a 6-cause taxonomy (`references/thrash.md`: ambiguous
  target / no plan / too big / stale context / patching-the-patch / wrong lever),
  lands ONE upstream lever, records it in `actions[]` with a thrash-rate expected
  effect so Step 0 verifies. Coach Step 1b flags thrash and hands off to `/retro`.
  Hard line: the prompt is NEVER graded — the plugin measures shape and coaches from
  what the user volunteers; policy-safe because the user brings the content.
  knowledge_version 4 → 5.

## Done in v0.10.1 (confidence grading + contradiction, 2026-07-16)

Borrowed the good half of Cursor Team Kit's `workflow-from-chats` confidence model
(strong/medium/weak/contradicted) — but grounded on OBSERVED events, not chat
statements, so contradiction rests on hard signals (ratio, `capabilities.used`), not
"you said otherwise in a chat."

- [x] **[MINOR] Nominations weren't graded — noise risk** — `session_shapes.py` now
  emits `friction_confidence` per category, `category_sessions`, and a `confidence`
  grade on every `unused_lever_warrants` and `thrash_sessions` entry (deterministic:
  recurrence ≥2 sessions + ratio ≥0.6 → strong; proxy-only warrants → weak). Coach
  orders strong→medium, ≤2/run, and — per the "no padding" precedent — **never
  nominates a weak finding as a problem**; weak graduates to medium on recurrence, and
  on a no-friction run may only seed a gentle teach. A `/log` note upgrades one tier.
- [x] **[MINOR] Self-report could go unchallenged** — `contradicted` is now a
  first-class outcome across coach/retro/score: a claim the journal negates ("tests
  always fail" but ratio <0.3; "I always use plan mode" but `plan_mode.used==false`;
  a refusal contradicted by recurring friction) is not nominated or accepted — pause
  and ask. Protects the user-volunteered `/retro` account from sending the diagnosis
  to the wrong cause. New constants `STRONG_MIN_SESSIONS=2`, `CONTRADICT_RATIO=0.3`.
  No credit/cap math changed → knowledge_version stays 5 (behavior + pacing only).

## Done in v0.10.2 (fix rationale, 2026-07-17)

- [x] **[MINOR] Actions recorded WHAT and the expected metric, but not WHY** (idea from
  SIA's `improvement.md` rationale artifact). `actions[]` now carries a one-line
  `rationale` — the hypothesis for why this lever fixes this friction. At Step-0
  verification the coach can judge whether the reasoning held, not just whether the
  number moved: a fix that worked for a different reason is a weaker lesson. Recorded by
  coach + retro; schema + persistence contract updated.

## Done in v0.11.0 (score/friction trajectory in show, 2026-07-17)

- [x] **[MINOR] `/show` showed a static card, no progress-over-time** (idea from SIA's
  accuracy-across-generations dashboard, adapted to "friction across runs"). New
  `scripts/score_trajectory.py` turns `history[]` into terminal unicode sparklines
  (deterministic — the script picks glyphs, not the LLM): score, friction rate,
  per-axis trends, and the verified-fix tally, each with a first→last delta and a
  trend flag (float-epsilon so threshold deltas read consistently). `/show` renders it
  verbatim when `runs >= 2`; on a single run it says the trajectory builds from run two.
  The real signal is the friction sparkline falling (▇▆▄▃▁ = your harness is cutting
  pain, not just the score rising). To feed it, `/score` now snapshots
  `friction_per_100` (from session_shapes) into each `history[]` entry — it fills in
  going forward; older entries lack it. knowledge_version unchanged (display only).
  RU-docs terminology fixed alongside: the word for `turn` now means "prompt" (was a
  chess-move metaphor), since the event is a prompt submission.

## Done in v0.11.1 (show is screen-share-safe, 2026-07-17)

- [x] **[MAJOR] `/show` leaked the repo inventory** — the projects block printed every
  work repo name (NewPM, paysoft, …) onto what is explicitly a screen-share surface.
  Removed the per-project list from `/show` entirely; the only allowed repo signal there
  is a name-free aggregate ("N repos, median X"). Per-project readiness stays in the
  `/score` report (private). Display-only; no score math changed.

## Done in v0.11.2 (workspace scan was minutes-slow, 2026-07-17)

- [x] **[MAJOR] Secrets scan ran once per repo, sequentially** — a workspace of ~14
  repos on a /mnt (WSL) mount took minutes per `/score` (gitleaks scans each repo's
  full history at 120s/repo; the fallback reads up to 5000 files/repo). Two fixes:
  (1) **cache by HEAD** — `secrets_for()` caches the result in `state/secrets-cache.json`
  keyed by repo HEAD when the tree is CLEAN (dirty trees always rescan, since HEAD
  doesn't capture uncommitted files); repeat `/score` runs are near-instant. (2)
  **parallel** — workspace repos scan in a thread pool (I/O-bound → real speedup;
  order preserved). Result carries `cached: true` when served from cache. Perf only;
  no score/credit change.

## Open — candidates for v0.5+ (need real usage data or bigger design)

- [ ] **[MAJOR] Academy module map** — the score skill demands "a specific module," but no
  module index ships → hallucinated names. Build a versioned `references/academy.md`
  map + a scorecard field for completed modules to skip. Until then, the skill should
  fall back to "next practical task in your repo" and NOT name a module it can't verify.
  *(Interim mitigation shipped in v0.4.0: score skill now forbids inventing module names
  and defaults to the repo task alone; the versioned module map is the remaining work.)*
- [ ] **[MINOR] Statistical significance helper** — Step 0's "≥5 events, post-window ≥
  pre-window, below pre-spike baseline" is spec'd in prose but LLM-eyeballed. Consider a
  tiny `verify_action.py` that takes the journal + action and returns strong/weak/none
  deterministically, so the verdict isn't a judgment call.
- [ ] **[MINOR] Per-user recurring-gap learning** — `session_shapes.py` could learn each
  user's habitual daily gap times (meals/meetings are same-time across days) to suppress
  O1 false positives structurally, not just via the compaction conjunct.
- [ ] **[MINOR] Monthly digest** — SessionStart reminder only fires on pending friction;
  a once-a-month one-liner ("score 72→75, oversight flat") would sustain the self-race.
- [ ] **[MINOR] Score-simulator: model the F axis** — the docs simulator can't show F
  (needs history); a "second run" toggle could demonstrate the F-entry two-score split.
- [ ] **[QUESTION] Weights 2.0/1.5/1.0 are hand-picked, not calibrated.** Once there's a
  corpus of runs, check whether the items that carry weight actually predict friction
  reduction; re-weight empirically. Bumps knowledge_version when it lands.

## Known gaps to disclose (not bugs — stated limits)
- Score is self-assessed from data the user controls; defensible as "harness maturity,"
  never as third-party certification.
- `permission_denied` only fires under the auto-mode classifier; default-mode "No"
  clicks are invisible. The coach leans on `permission_request` rate instead.
- No transcript access by policy → prompt quality and "wrong approach" are unmeasured by
  design; the plugin measures outcomes, not prose.
