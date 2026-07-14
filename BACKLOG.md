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

## Open — candidates for v0.5+ (need real usage data or bigger design)

- [ ] **[MAJOR] Log tool successes per category** (counts only, no content) so a failure
  *ratio* exists — a heavy productive day is currently indistinguishable from a bad one.
  Needs a new signal source: PostToolUse success isn't a current hook event we collect;
  investigate whether a lightweight success counter is worth the per-turn cost.
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
