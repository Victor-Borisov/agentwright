# Lever library

Vetted recipes for the coach's Step 4. Match the friction signature first; improvise
only when nothing here fits. Every recipe states what it guarantees, what it costs,
the artifact template, a **proof test** (run it before applying — HIGH-cost levers
must demonstrate the blocking exit code), and the **expected-effect metric** to write
into `scorecard.actions[].expected` so Step 0 can verify it later.

Guarantee ladder (always present the tradeoff to the user this way):
**rule in CLAUDE.md** = a wish, free, sometimes ignored → **hook** = a guarantee,
costs latency on every event → **CI gate** = the hard stop, costs cycle time.

---

## L1 · Test gate on edits

**Friction signature:** `tool_failure` events with `category: test` recur across
sessions; "it broke the tests again" manual notes.
**Guarantees:** tests run after every file change, failures surface immediately to
the agent (feedback loop, checklist B2).
**Costs:** test-suite latency on every edit — WRONG lever if the suite is slow
(> ~30s: use L2 or a scoped test subset instead; a slow hook gets ignored or hated).

Artifact — project `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "<fast test command, e.g. npm test -- --changed>" }]
      }
    ]
  }
}
```
**Proof test:** break a trivial assertion, edit a file, confirm the hook output shows
the failure; restore. A hook that cannot fail is decoration.
**Expected effect:** `tool_failure/test rate per 100 turns drops in <project>`.

## L2 · Pre-commit gate (tests and/or lint)

**Friction signature:** test/lint failures discovered late; commits that break CI.
**Guarantees:** nothing broken gets committed. **Costs:** commit latency; only on
commit (later than L1 in the cycle).

Artifact: `.pre-commit-config.yaml`, husky, or a plain `.git/hooks/pre-commit`:
```bash
#!/usr/bin/env bash
npm test || exit 1   # MUST propagate the non-zero exit code
```
**Proof test:** with a failing test, `git commit` must abort (non-zero). The classic
silent defect is a trailing `exit 0` — check for exactly that.
**Expected effect:** `tool_failure/test rate drops; no revert-style git activity after commits`.

## L3 · Lint-on-edit hook

**Friction signature:** `category: lint` failures recur; style nitpicks keep coming
back in review.
**Guarantees:** immediate, deterministic style feedback to the agent.
**Costs:** small latency; noisy if the linter config is immature — fix the config first.

Artifact — same PostToolUse shape as L1 with the lint command (`ruff check --fix`,
`eslint --fix`, …). Prefer auto-fixing linters: the agent then sees only real leftovers.
**Proof test:** introduce a lint violation, edit the file, confirm the hook reports or fixes it.
**Expected effect:** `tool_failure/lint rate per 100 turns drops`.

## L4 · Permission tuning (allow/deny)

**Friction signature:** high `permission_request` rate per session; `permission_denied`
events; the user complains about constant approval prompts.
**Guarantees:** fewer interruptions with safety preserved — deny-list blocks the
destructive, allow-list frees the routine read-only.
**Costs:** one-time analysis; too-broad allow = a hole (this is a HIGH/security lever —
always reviewed).

Procedure, not a file: run the built-in `/fewer-permission-prompts` skill, or add to
user/project `settings.json`:
```json
{
  "permissions": {
    "allow": ["Bash(git status*)", "Bash(git diff*)", "Bash(ls*)"],
    "deny":  ["Bash(rm -rf*)", "Bash(git push --force*)", "Bash(*DROP TABLE*)"]
  }
}
```
**Proof test:** the denied command must actually be blocked; the allowed one must not prompt.
**Expected effect:** `permission_request rate per 100 turns drops with deny_count unchanged or higher`.

## L5 · Destructive-command guard

**Friction signature:** none needed — this is a baseline security item (S5); also any
near-miss manual note ("almost nuked the folder").
**Guarantees:** the irreversible is impossible, not just discouraged.
**Costs:** occasional false positive on legitimate commands — keep patterns narrow.

Artifact: deny rules as in L4, or a PreToolUse hook returning
`{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` for matched patterns.
**Proof test:** each guarded pattern actually blocks; a harmless neighbor command passes.
**Expected effect:** `S5 present; zero destructive incidents (this lever is insurance — verified by non-events)`.

## L6 · CLAUDE.md rule

**Friction signature:** the agent repeats a project-specific mistake that a
*convention* would prevent (wrong directory, wrong framework idiom, forgets a step
that is cheap to state); low-stakes, high-frequency.
**Guarantees:** nothing — it is a wish the model usually honors. That is the point:
zero latency, zero machinery. WRONG lever when a guarantee is needed (then L1–L5).
**Costs:** context tokens; rules rot — pair with periodic pruning (checklist E2).

Artifact: one imperative line under an existing CLAUDE.md section, concrete and
testable ("Run `make gen` after editing any `.proto` file"), never a platitude.
**Proof test:** none possible (that's the tradeoff — say so to the user explicitly).
**Expected effect:** `related tool_failure/manual rate drops; if not, escalate to a hook next review`.

## L7 · Context hygiene rule

**Friction signature:** `compact` events cluster in long sessions; quality degrades
late in sessions; "it forgot what we were doing" notes.
**Guarantees / costs:** habit-level fix, cheap; escalate to subagent isolation for
big searches if it recurs.

Artifact: user-level CLAUDE.md rule ("Start unrelated tasks with /clear"), plus using
subagents for wide exploration instead of dumping files into the main context.
**Expected effect:** `compact rate per 100 turns drops`.

## L8 · Blocking CI gate

**Friction signature:** breakage reaches the shared branch; L1/L2 exist but get
bypassed; team context.
**Guarantees:** the hard stop before merge — required checks + branch protection.
**Costs:** cycle latency; CI maintenance. HIGH-cost: review the workflow before applying.

Artifact: `.github/workflows/ci.yml` running tests/lint with `required` status checks
enabled on the branch.
**Proof test:** a PR with a failing test must show a red, merge-blocking check.
**Expected effect:** `checklist B3 present; post-merge failure notes disappear`.

---

## Choosing between levers — the two questions

1. **Does this need a guarantee, or is a wish enough?** Repeated damage or security →
   hook/gate (L1–L5, L8). Cosmetic or occasional → rule (L6–L7). "Nothing" is a valid
   answer too — rare friction with a fast manual fix does not deserve machinery.
2. **How expensive is the check?** Fast → as early as possible (on-edit hook). Slow →
   as late as tolerable (pre-commit, CI). Never attach a slow check to a frequent event.
