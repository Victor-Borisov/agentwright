# Maintaining Agentwright

How the plugin keeps up with a growing Claude Code. The architecture puts growth
into the data layer (`references/*.md`), so most maintenance is editing markdown —
this file makes the procedures explicit so they survive maintainer memory.

## The backlog is the memory

`BACKLOG.md` tracks every known improvement (done + open), sourced from adversarial
reviews. Rules: re-run the three-critic review (technical / methodology / consistency
lenses) after any major version; every finding lands in BACKLOG as `[ ]`/`[x]`/`[~]`
with severity; open items that need real usage data stay open with the reason. Never
silently drop a finding — mark it `[x]` with the version or move it to "known gaps".

## Versioning contract

| Thing | Where | Bumps when |
|---|---|---|
| Plugin version | `.claude-plugin/plugin.json` | any release (semver: knowledge additions = minor, fixes = patch) |
| `knowledge_version` | `references/calibration.json` | checklist/levers/opportunities items added, removed, or rescoped |
| `calibrated_for_claude_code` | `references/calibration.json` | after each changelog sweep, even if nothing was added |
| Scorecard `checklist_version` | written by the score skill | follows `knowledge_version` |

The score report is contractually obliged (scoring.md § Evolution contract) to split
deltas into "your changes" vs "the bar moved" whenever `checklist_version` changes —
never ship a knowledge update without that machinery intact.

## Monthly refresh (or when the staleness notice fires)

Run `/agentwright:refresh` in a session started with `--plugin-dir` on this repo.
It fetches the official changelog, triages new capabilities (what pain does it
remove / what does missing it look like / does it need a recipe), drafts rows for
your approval, and bumps the calibration. Budget: ~30 minutes.

Manual fallback: read https://code.claude.com/docs/en/changelog.md since
`calibrated_for_claude_code`, apply the same three triage questions, edit the
references, bump versions per the table above.

## Add-a-signal checklist (new hook event worth collecting)

1. `hooks/hooks.json` — add the event → `collect-friction.sh <event_name>`.
2. `scripts/collect-friction.sh` — extend the classifier only if the event carries
   a classifiable payload; remember: derived categories only, never raw text.
3. `scripts/session-start.sh` — add the event to the friction grep filter ONLY if
   it represents felt pain (cadence/denominator events stay out of the alarm).
4. `skills/coach/SKILL.md` — add a row to the journal vocabulary table (friction /
   rate signal / denominator).
5. `scripts/session_shapes.py` — nothing to do (event-agnostic) unless the event
   should join `FRICTION_EVENTS` for normalized totals, `CAP_MAP` for capability
   presence, or a new aggregate (`failure_ratio`, `effort_distribution`,
   `unused_lever_warrants`).
6. `scripts/collect_friction.py` — extend `CLASSES` only if the event carries a
   classifiable Bash command. For capability events, add the tool to the landscape
   matcher in hooks.json and a label to `CAP_MAP`; the .sh is a thin wrapper.
7. `scripts/scan_artifacts.py` — mirror any new journal aggregate the `/score` skill
   needs (it reads scan output, not session_shapes) — e.g. `capabilities_used`.
   Note: the per-repo secrets scan is cached in `state/secrets-cache.json` keyed by
   repo HEAD (clean trees only) and repos scan in parallel — if you change what the
   secrets scan returns, the cache carries the OLD shape until HEAD changes; bump/clear
   the cache file or key it on a version if the result schema changes.
   `scripts/score_trajectory.py` — if you add a NEW per-run `history[]` field that is a
   time series (like `friction_per_100`), add a sparkline line for it here and have
   `/score` snapshot it into the history entry; `/show` renders whatever this emits.
8. Docs (all of them): README "Signal journal" bullet + the `#day` flow node and
   privacy "Reads" list in BOTH `docs/index.html` AND `docs/index.ru.html`.
9. Test with a synthetic stdin JSON (see the Testing section below).

**Two hard rules for new signals.** (a) PRIVACY: persist only a derived category, a
safe tool label, or a counter — never raw text; MCP tool names (`mcp__server__tool`)
MUST collapse to `mcp` (server names are private infra, like the work repo names that
once leaked). (b) COST: `PostToolUse` on `Bash` fires on every successful shell
command — it is the one high-volume hook. Keep its handler trivial (classify +
append), drop `other`-category successes (noise), and remember a user bothered by
latency can delete just that one hook entry. Never subscribe a BLOCKING hook
(`PreToolUse`, `WorktreeCreate`, `PostToolBatch`) for mere logging.

## Testing before release

```bash
# syntax
for f in scripts/*.sh; do bash -n "$f"; done
python3 -m py_compile scripts/*.py
python3 - <<'EOF'
import json; [json.load(open(f)) for f in
 ('.claude-plugin/plugin.json','hooks/hooks.json','references/calibration.json')]
EOF

# exec-bit independence — repos on Windows mounts (and some install paths) lose
# the executable bit, so every invocation of a plugin script MUST go through an
# explicit interpreter (`bash …/x.sh`, `python3 …/x.py`); a bare "${CLAUDE_PLUGIN_ROOT}"/…
# in hooks.json or a SKILL.md dies with "Permission denied" (126) on such installs.
grep -rn '"\${CLAUDE_PLUGIN_ROOT}"*/scripts' hooks/ skills/ | grep -vE 'bash |python3 ' && echo "FIX: bare script invocation" || echo OK

# behavior — always against an isolated HOME
FH=$(mktemp -d)
echo '{"session_id":"t1","cwd":"/tmp/Proj","tool_name":"Bash","tool_input":{"command":"npm test"}}' \
  | HOME="$FH" scripts/collect-friction.sh tool_failure
HOME="$FH" scripts/scan-artifacts.sh "$FH"
HOME="$FH" python3 scripts/session_shapes.py

# language guard — plugin internals are English-only; translated docs
# (docs/*.ru.html) are the sanctioned exception and must stay in sync with
# their English originals on every docs change. MAINTAINING.md is excluded
# because the style-guard pattern below itself contains Cyrillic.
grep -rPln --exclude='*.ru.html' --exclude=MAINTAINING.md '[\x{0400}-\x{04FF}]' . && echo "FIX: non-English content" || echo OK

# style guard — never use honesty-vouching words ("honest", "honestly",
# "честно"): vouching for one statement casts doubt on every other. State the
# fact; don't certify it.
grep -rniE --exclude=MAINTAINING.md 'honest|честн' . && echo "FIX: honesty-vouching wording" || echo OK
```

## Product metrics — is the plugin itself working?

The plugin measures the user; these measure the plugin. Three metrics, in funnel
order, each answering one question:

| Metric | Question | Measured by |
|---|---|---|
| **Activation** | installed → first `/score` baseline | `scorecard.json` gains its first `history[]` entry; time from first journal event to it |
| **Core value ("aha")** | did a coached fix *verifiably* cut friction? | first `actions[]` entry with `verified: true` — this is the product promise; if users never reach it, nothing else matters |
| **Retention** | is the loop alive? | journal events + `flags/reviewed-*` in the trailing 28 days |

`scripts/product_metrics.py` computes the funnel from local data (dates and counts
only, `--json` for machine-readable). Run it on your own machine while dogfooding;
ask beta users to paste its output voluntarily — that is the only sanctioned
cross-user channel, because the plugin transmits nothing by design. Everything else
is proxies: GitHub stars/clones/issues, and a pinned "share your funnel" issue.

Release rule of thumb: a change that does not plausibly move one of the three
metrics (or fix a defect) is backlog, not scope.

## Hard privacy lines (never relax these)

- Field findings entering BACKLOG, skill examples, or docs must be ANONYMIZED before
  commit: no real project/repo/folder/server names from the maintainer's (or any
  user's) machines — describe the shape ("a workspace root with several clones"),
  invent neutral example names ("backend-api"). Git history is public and forever;
  a name that slips through requires a history rewrite, not just a follow-up commit.

- No reading `~/.claude/projects/`, `~/.claude/usage-data/`, or any
  conversation-derived data (Anthropic Software Directory Policy §1.D/§1.F).
- Journal stores derived categories and counters — never command text, prompt
  text, tool outputs, or file paths.
- No network calls from the plugin. Anything that would ever transmit data must be
  a separate, strictly opt-in component with its own consent flow — never this plugin.
- No state-changing actions, ever — not to verify a finding, not to test a guard.
  The plugin only READS (files, config, guard source) and appends to its own journal.
  It must never issue a write/DDL/delete/force-push/destructive-shell against any
  target on any tier. Guards are assessed by reading their code path. (Field find
  2026-07-14: a score run executed `create/insert` on a live DB to prove an MCP
  validator bypass — exactly the line this rule draws.)
