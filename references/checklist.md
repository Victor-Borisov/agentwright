# Agentwright Checklist

**Knowledge version: 2 · calibrated for Claude Code 2.1.x** (see
`calibration.json`). Items added in later knowledge versions must carry a
`(new in vN)` marker until scored once — the score report treats them as "the bar
moved", never as user regression (see scoring.md § Evolution contract).

Every item is scored with one of four credit-bearing statuses (`present`,
`conscious_refusal`, `partial`, `absent`), plus `not_assessed` (excluded from the
denominator):

| Status | Meaning | Credit |
|---|---|---|
| `present` | Artifact exists with authorship history (git dates / file mtimes — checkable facts; claimed "usage" is not observable and is never pretended to be checked) | 1.0 |
| `conscious_refusal` | Absent, but the user names the lever, its tradeoff, and a concrete reason it does not fit their context | 1.0 |
| `partial` | Exists but weak (e.g. generic CLAUDE.md, allow-list without deny-list) | 0.5 |
| `absent` | Missing and the user did not know the lever exists | 0.0 |
| `not_assessed` | Probe impossible in this environment | excluded from denominator |

**Conscious-refusal quality bar.** A refusal is credited ONLY if the answer shows the
user knows the lever (what it guarantees, what it costs) and gives a context-specific
reason. "I don't need it" without a why = `absent`. "My tests take 20 minutes so I gate
in CI instead of a pre-commit hook" = credited, and marks knowledge of BOTH levers.

**Grounding rule.** Never set `present` without probe evidence from `scan-artifacts.sh`
output or an explicit user statement in this conversation. Never invent facts. If the
probe cannot run: `not_assessed`.

Axes: `[L]` landscape · `[J]` judgment · `[O]` oversight · `[X]` outcome.
Cost: `HIGH` = security / built into the harness / irreversible → oversight expected.
`CHEAP` = easily reversible → skipping review there is maturity, not negligence.

---

## S — Security layer (gate, probed first)

| ID | Item | Axis | Cost | Probe |
|---|---|---|---|---|
| S1 | No secrets in repo files or git history | X | HIGH | `repo.secrets` (gitleaks or patterns) |
| S2 | secret-shaped files are git-ignored (`.env`, keys, certs) — any ignore source counts for the user, committed `.gitignore` for the project (rescoped in v2) | X | HIGH | `repo.env_ignore` (effective, any source) / `repo.gitignore_env_covered` (committed) |
| S3 | Permissions narrowed: deny-list on destructive commands exists; no `allow: ["*"]`; not living in `bypassPermissions` | X | HIGH | `user.settings` + `project_level.settings`; journal `permission_request` rate shows tuning quality |
| S4 | MCP tokens via env vars, not plaintext; servers of known origin | X | HIGH | `*.mcp.plaintext_secret_suspect` |
| S5 | Destructive-command guard (deny rules or PreToolUse hook for `rm -rf`, force-push, `DROP TABLE`) | X | HIGH | settings deny entries / hooks |

**Security gate:** any S item at `absent` with an actual live finding (e.g. real secret
found) caps the total score at **59** (below the Builder threshold). An S item merely
`partial` — or `not_assessed` (unverified security cannot be Architect, and better
probes must never lower a score relative to no probes) — caps at **84** (below the
Architect threshold). Caps are level boundaries minus one — see scoring.md. Report
the cap explicitly and put fixing it first in the growth plan.

## A — Context & memory

| ID | Item | Axis | Cost | Probe |
|---|---|---|---|---|
| A1 | Project CLAUDE.md exists and is substantive (not generic platitudes; >10 lines or uses @imports) | X | CHEAP | `project_level.claude_md` + read it |
| A2 | User-level CLAUDE.md with personal conventions | X | CHEAP | `user.claude_md` |
| A3 | Lessons captured into persistent artifacts (memory files, dated rules) | X | CHEAP | `user.memory_files` |

## B — Guarantees & feedback loops

| ID | Item | Axis | Cost | Probe |
|---|---|---|---|---|
| B1 | Hooks in active use (any lifecycle event beyond this plugin's own) | X | HIGH | settings/plugins `hooks_events` |
| B2 | Automatic quality loop: lint/test on edit (hook) or pre-commit | X | HIGH | `repo.precommit`, hooks |
| B3 | CI gate that blocks (not just warns) on failure | X | HIGH | `repo.ci_workflows` + dialog |

## C — Delegation primitives

| ID | Item | Axis | Cost | Probe |
|---|---|---|---|---|
| C1 | Custom skills/commands exist for repeated work | X | CHEAP | `user.skills+commands`, `project_level.*` |
| C2 | Custom subagents defined where isolation/role-split helps | X | CHEAP | `user.agents`, `project_level.agents` |
| C3 | MCP integration where the project genuinely needs external data — or a credited refusal | J+X | CHEAP* | `*.mcp` + dialog (*security side is HIGH, covered by S4) |

## D — Judgment & landscape (dialog-based; not observable in artifacts)

Ask these IN CONTEXT — as choices about the user's real situation, never as quiz
definitions. One good situational answer proves both landscape and judgment.

| ID | Item | Axis | Cost |
|---|---|---|---|
| D1 | Given a real friction from the journal: picks an appropriate lever (rule / hook / CI / MCP / nothing) and justifies by consequences | J+L | CHEAP |
| D2 | Uses plan mode as the entry point for non-trivial multi-file tasks — or credited refusal | J | CHEAP |
| D3 | Knows the guarantee ladder: rule (wish) → hook (guarantee, costs latency) → CI (hard gate, costs cycle time) — demonstrated by D1-style answers, not recitation | L | CHEAP |
| D4 | Manages context deliberately (/clear between tasks, compact awareness, subagent isolation for big searches) — cross-check with journal `compact` rate per session | L+J | CHEAP |
| D5 | Assigns models/effort by task (premium for hard, small for routine) — or credited refusal | J | CHEAP |
| D6 | Uses parallelism when appropriate (worktrees, background agents) — or credited refusal | L | CHEAP |

## E — Oversight (only at HIGH-cost points)

| ID | Item | Axis | Cost | Probe |
|---|---|---|---|---|
| E1 | Reviews artifacts that embed into the harness (hooks, permission changes, MCP configs) before applying; consciously skips review of cheap one-offs | O+J | HIGH | dialog + coach-loop behavior |
| E2 | Periodically prunes the harness: notices rules/hooks that false-positive and removes them | O | HIGH | dialog + journal evidence |

## F — Effect (needs history; scored from the 2nd run onward)

| ID | Item | Axis | Cost | Probe |
|---|---|---|---|---|
| F1 | Levers applied against past frictions actually reduced them (verified in coach Step 0) | X | — | `scorecard.actions[].verified` |
| F2 | Friction trend over the last N reviews is flat-or-down while activity continues | X | — | journal aggregates |

First run: F items are `not_assessed` (excluded), so a strong first-run setup can still
score high — matching the principle that a senior with no friction and good reasons
starts high immediately.
