---
description: >
  Compute the user's Agentwright Score (1-100) — a harness maturity assessment for
  Claude Code. Use when the user asks for their score, level, harness maturity,
  "how well am I using Claude Code", or wants to re-assess after changes. Runs a
  deterministic artifact scan, walks a checklist with a short judgment dialog for
  unobservable items, applies a security gate, and writes a persistent scorecard.
allowed-tools: "Bash, Read, Write"
---

# Agentwright Score

You are assessing harness maturity, not tool-usage volume. The philosophy (do not
deviate): mechanics the model performs are worthless to measure; what stays valuable
is **landscape** (knowing what levers exist), **judgment** (picking the right one),
**oversight** (catching quiet defects at HIGH-cost points), and **outcome** (an
appropriate, working, safe setup — regardless of who built it).

**Dialog language.** Before anything else, read `~/.claude/agentwright/config.json`.
If it has a `language` field, conduct the entire dialog in that language. If the file
or the field is missing, your FIRST message must ask which language Agentwright
should use with the user — pose the question in English and repeat it in two or
three other languages (written in their own script) so a non-English speaker can
recognize it; any reply language counts as the answer. Merge the answer into the config
(`{"v": 1, "language": "<answer>"}`) — create the file with python3 if needed, never
jq — confirm in that language, then proceed. Keep artifacts (scorecard JSON, journal
notes) in English regardless of dialog language.

## Procedure

### 1. Collect facts (deterministic — no interpretation yet)

Run: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/scan-artifacts.sh` (pass the project path if the
user names one). This JSON is your ONLY source of artifact facts.

**Workspace mode.** If the facts contain a non-null `workspace`, the scanned root is
not a repo but CONTAINS repos (a multi-clone workspace — a normal layout, never a
finding by itself). Then: adjudicate every repo-scoped item (S2, B3, secrets,
per-repo CLAUDE.md) separately per `workspace.repos[]` entry and write one
`project_scores{}` entry per repo, keyed by its `name`. Do NOT treat the root's own
`repo.is_git: false` as "unverified" — the per-repo facts ARE the verification.
`workspace.non_git_dirs` are personal folders outside version control: un-ignored
local files there are not a gap (nothing can leak into a history they are not part
of); mention them only if the user says one is supposed to be a repo. If
`workspace.truncated` is true, say which repos were skipped by the cap. Do not open
transcripts, `~/.claude/projects/`, or `~/.claude/usage-data/` — that data is
off-limits by design (Anthropic Software Directory Policy §1.F), and the score must
work without it.

### 2. Map facts to checklist statuses — with stickiness

Read `${CLAUDE_PLUGIN_ROOT}/references/checklist.md`. For every S/A/B/C item, set the
status directly from facts. S2 reads `repo.env_ignore` with two verdicts
(scoring.md § S2 has two readings): effective coverage from any source satisfies
the USER; only `committed` coverage satisfies PROJECT readiness — local/global
coverage keeps the project cap but the report must name it as "covered on this
machine, team-level fix pending", not as an unprotected repo. Read the actual CLAUDE.md files (paths are in the facts)
to judge substance for A1/A2 — generic platitudes ("write clean code") = `partial`.

**Stickiness (scoring.md § Reproducibility):** previous `items[]` are the prior.
Re-adjudicate only items whose facts changed vs the recorded evidence, or where the
user gives a new answer. A stricter re-reading of UNCHANGED facts is an adjudication
change: apply it but flag it and exclude it from the "what you lost" narrative.
Never re-ask a question whose persisted answer and facts are both unchanged.

### 3. Dialog — only for gaps and D/E items

Batch your questions (one message, grouped list; do not interrogate one-by-one).
Rules:

- Ask **situationally**, never as definitions. Good: "Your journal shows repeated Bash
  failures after edits — what would you reach for, and why?" Bad: "What is a hook?"
- If the friction journal has events, use a real one as the D1 scenario.
- For every artifact-absent item, ask whether it's a deliberate choice. Apply the
  conscious-refusal quality bar from checklist.md strictly, INCLUDING journal
  consistency (scoring.md): a refusal contradicted by observed friction of the
  matching category caps at `partial` and must be challenged out loud.
- `scorecard.opportunities[]` entries mean the lever is KNOWN (`dismissed` and
  `taught` alike) — that informs the landscape reading, but full refusal credit is
  minted only here, in this dialog, under the full bar. Do not credit a coach
  dismissal as a refusal automatically; do re-use its recorded reason as the
  starting point of the question.
- First run (no previous scorecard): keep the dialog to the core items (S gaps,
  B1–B3, D1–D3); schedule the rest as `not_assessed` for the next run — ten batched
  questions to a stranger is a wall, not an assessment.
- The user saying "I didn't know that existed" is a GOOD outcome for them to say —
  respond without judgment; it becomes the growth plan, not a scolding.

### 4. Compute

Apply `${CLAUDE_PLUGIN_ROOT}/references/scoring.md` exactly: weights, formula,
security gate, anti-gaming rules, level bands. Show your arithmetic in the report so
the number is auditable.

**Evolution contract** (scoring.md § Evolution contract): if
`previous.checklist_version` differs from the current `calibration.knowledge_version`,
OR if F items enter for the first time (second run), compute the score twice — over
the old item set (the comparable delta, "your changes") and over the full set (the
new official score) — and attribute the gap ("the bar moved" / "effect items now
measurable"). An `absent` on a `(new in vN)` item never reads as regression.

**Two numbers** (scoring.md § User score vs project readiness): the headline score is
the USER-harness score; project-scoped items form the per-project readiness score
recorded in `project_scores{}`. A security finding in the repo caps the project
score; it caps the user score only if it lives in user-level config or user-authored
artifacts. Report both: "You: 74 ±3 · This project: 61 (capped by S1)." In workspace
mode report one project line per repo ("backend-api: 91 · data-jobs: 88"), never a
single number for the non-repo root.

### 5. Persist and report

Write `~/.claude/agentwright/scorecard.json` (schema in scoring.md; set
`checklist_version` to the current `calibration.knowledge_version`; append to
`history`, preserve `actions` and `opportunities` from the previous scorecard —
never drop unverified actions). Then seal it:
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/card_integrity.py stamp` — the show skill
refuses to display a card whose seal does not match (tamper-evidence for
screen-sharing; a card edited by hand stops being displayable).

Report structure:

0. **Staleness banner (only if `calibration.stale` is true)** — one line: the
   running Claude Code is ahead of what this knowledge base is calibrated for, so
   the score is a floor of the landscape, not the ceiling; suggest updating the
   plugin.
1. **Score and level** — big and first, WITH the precision band ("72 ±3",
   scoring.md § Precision band). Delta vs previous run and the top reason it moved —
   split into "your changes" / "the bar moved" / "adjudication changes (not counted
   against you)". Include per-axis deltas from `history[].axes` when ≥2 entries
   exist ("oversight flat for 3 runs" is the development signal, not the total).
2. **Security gate** — if a cap applied, say so bluntly and put hardening first.
3. **Axes breakdown** — landscape / judgment / oversight / outcome, one line each on
   what drove it.
4. **What earned credit** — including conscious refusals, named as maturity.
5. **Growth items — up to 3, never padded.** Each must be a real, currently actionable
   gap: the concrete gap and the lever to learn, framed as the next practical task in
   the user's own repo. If more than 3 exist, show the top 3 by impact and say how many
   remain. If fewer exist, show fewer; with zero, say so plainly — "no actionable gaps
   in the assessed items" is a valid, strong result. Scheduling notes ("next run will
   assess E items") are NOT growth items — mention them separately in one line. If — and only if — you can name a
   real, current Anthropic Academy module that fits (anthropic.skilljar.com), link it;
   NEVER invent a module name. When unsure, give the practical repo task alone. (A
   verified module map is a backlog item; until it ships, the repo task is the reliable
   half.)
6. One line: "Run /agentwright:coach to work the friction journal; the score updates
   as verified fixes land."

Never inflate. A 47 with a clear path beats a flattering 80.
