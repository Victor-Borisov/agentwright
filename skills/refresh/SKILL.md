---
description: >
  Maintainer tool: sweep the latest Claude Code release notes and refresh
  Agentwright's knowledge base (checklist, levers, opportunities) with new
  capabilities. Use when the maintainer asks to refresh/recalibrate the plugin's
  knowledge, or when the staleness notice reports Claude Code is ahead of the
  calibration. Not part of the end-user scoring/coaching flow.
disable-model-invocation: true
allowed-tools: "WebFetch, Read, Edit, Write, Bash"
---

# Agentwright — knowledge refresh (maintainer)

Goal: every Claude Code capability added since the last calibration either enters
the knowledge base or is explicitly skipped with a reason. The maintainer decides;
you triage and draft.

## Procedure

1. **Establish the gap.** Read `${CLAUDE_PLUGIN_ROOT}/references/calibration.json`
   and the locally observed version (`~/.claude/agentwright/state/cc-version`, or
   run `claude --version`). Fetch the official changelog:
   `https://code.claude.com/docs/en/changelog.md`. Collect entries newer than
   `calibrated_for_claude_code`.

2. **Triage each new capability with three questions** (skip internal fixes and
   pure UI polish):
   - What recurring pain does it remove, for whom?
   - What does *missing* it look like — is there an observable signature in our
     journal metadata (→ opportunities.md row with thresholds), or is it
     dialog-only (→ opportunities O9 list + a checklist D item)?
   - Does it need a vetted recipe with a proof test (→ levers.md row)?

3. **Draft the rows, show the diff, wait for approval.** Additions land as:
   checklist items marked `(new in vN)`, opportunity entries with detector
   contract intact, lever recipes with proof tests. The maintainer reviews before
   any file is written — judgment stays with the human, same philosophy the plugin
   teaches.

4. **On approval, bump the contract** (per `MAINTAINING.md` versioning table):
   - `calibration.json`: update `calibrated_for_claude_code`, `calibrated_on`;
     increment `knowledge_version` IF any checklist / levers / opportunities items
     were added, removed, or rescoped (not checklist-only — a levers- or
     opportunities-only change still bumps it, or the evolution contract is bypassed).
   - Update the version line in `references/checklist.md`.
   - `.claude-plugin/plugin.json`: bump minor version for knowledge additions, patch
     for fixes; a sweep that added nothing bumps neither (calibration date only).
   - If a new hook event became worth collecting, follow the add-a-signal
     checklist in `MAINTAINING.md`.

5. **Sync user-facing docs** (`README.md`, `docs/index.html`, AND `docs/index.ru.html`
   — the translation must never drift) if user-visible behavior changed, and finish
   with a short changelog note for the plugin release.
