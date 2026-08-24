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
| Marketplace entry version | `.claude-plugin/marketplace.json` | in lockstep with the plugin version, same commit — release-check fails on drift, and the CLI's `plugin tag` subcommand validates the pair at tag time |
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
9. Any new `.py` entry point that a skill, hook, or doc will invoke gets a `.sh`
   wrapper that sources `scripts/py-resolve.sh` — nothing outside `py-resolve.sh`
   may name an interpreter or probe PATH for one. Enforced by release-check in two
   places: the wrapper-integrity check (a `scripts/*.sh` doing python work must
   source the resolver, and no lookup or command-position interpreter form is
   allowed in any of them), and the invocation guard (a `python3`-prefixed
   `${CLAUDE_PLUGIN_ROOT}` call in hooks/skills/README is flagged — only `bash`
   wrapper calls pass). Residual gap: an interpreter named in prose outside those
   scan sets, or a plain-path call without the variable, is not machine-checked.
10. Test with a synthetic stdin JSON (`scripts/release-check.sh` does this in its
    isolated-HOME section; extend it for the new event).

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
bash scripts/release-check.sh    # exit 0 = clean, 1 = see the named failure
```

The checks live in the script, not in this file, so a release stops depending on
reading a paragraph. Three design rules the script enforces on itself, each learned
from a draft of this very file that shipped a detector printing `ok` while checking
nothing (a grep whose PCRE escapes never compiled; a guard block whose file list
arrived on a stdin the heredoc had already consumed; a per-line filter any
interpreter token could mask):

- **Every detector in the guard block carries a positive control.** Before
  scanning the tree, each one must flag a planted bad sample; a detector that
  cannot fire fails the run instead of passing it. The grep/diff checks outside
  the guard block (manifest pair, docs parity, syntax) carry no controls — they
  are single comparisons with fail-closed shapes, not pattern scans.
- **Text guards run in python, not `grep -P`.** PCRE `\x{}` escapes above 0xFF
  fail to compile without a UTF locale; grep then exits 2, and an `|| true`
  turns that into a silent pass. The python detectors have no locale dependency.
- **The file list is fetched inside the guard process and includes untracked
  files**, with a floor on files actually read — so the gate covers new files
  before `git add`, and an empty or unreadable tree fails instead of passing.

What the script asserts, and what each item catches:

| Check | What it catches |
|---|---|
| shell + python syntax, json parse | a broken edit reaching users; the json files are the two manifests, `hooks.json`, `calibration.json` |
| manifest pair agreement | the two version fields drifting apart — users receive updates only when both move |
| wrapper integrity | a wrapper regressing to its own interpreter handling: every `scripts/*.sh` doing python work must source `py-resolve.sh`, and no lookup (`command -v`, `which`, `type -p`) or command-position `python`/`python3` is allowed in any of them — the dead Windows alias resolves under a lookup and exits without running |
| language guard | non-English content in tracked and untracked text; `docs/*.ru.html` is the sanctioned translation; a text file that is not valid utf-8 fails the run rather than being skipped as binary |
| style guard | vouching wording — certifying one statement casts doubt on every other; state the fact plainly |
| invocation guard | a script call that dies without the exec bit or bypasses the wrappers: every `${CLAUDE_PLUGIN_ROOT}…/scripts/` occurrence in `hooks.json`, skills, and the README must be a `bash`-prefixed wrapper call, checked per occurrence, braced and unbraced variable forms alike |
| contract canaries | deletion of load-bearing coach prose: Step 0 preceding Step 1, the weak-finding suppression sentence, the journal-contradiction rule |
| docs parity | a translation that lost or gained a section — anchor sets must match, with an existence and size floor so two missing pages cannot pass as equal |
| isolated-HOME behavior | a script that only works because this machine's data directory is populated: all eight wrappers run against a throwaway HOME (both `HOME` and `USERPROFILE`, with a pre-flight that the interpreter agrees); the journal line, the manual note, the statusline echo and the interpreter cache are asserted, and `card_integrity` is driven through every documented exit code, corrupt json included (3/0/0/5/4/5) |

Not covered: `session-start.sh` behavior (needs a `claude` binary); an interpreter
named in prose outside the invocation-guard scan set or a plain-path call without
the variable; and whether the model OBEYS the prose contracts — the canaries only
prove the text is still there. The next section owns that last gap.

## Contract checks that are not automated yet

The load-bearing coach contracts live in markdown: verify past levers before
proposing new ones, never present a `weak` finding as a problem, never credit a
claim the journal negates. The release check now guards their TEXT (deletion is
caught deterministically by the canaries above), but not their OBEDIENCE — an
edit that keeps the sentence while rewording its context out of force still
passes, and only a scored run of the skill can catch that.

The instrument for obedience is the CLI's `plugin eval` subcommand. Interface per
`claude plugin eval --help` on CLI 2.1.241 (the help prints; the run itself
refuses with an early-access notice on this account): cases under `evals/` as
`case.yaml` or `prompt.md` plus `graders/*.md`; a baseline arm that runs the same
case WITHOUT the plugin and reports the score delta; `--runs` (default 3) for
repeated sampling; `--threshold` for a non-zero exit; `--report` for a
self-contained HTML report, `--no-publish` to keep it local. Retest the
entitlement at each monthly refresh or CLI update.

The three cases to write first. Prompt, grader, and pass criterion are specified
below; the FIXTURE FILES are still owed (an `evals/fixtures/` directory does not
exist yet), so this is a spec minus its artifacts, not a runnable suite — the
levers.md bar is met on two of its three elements:

1. **Step 0 first.** Fixture: a scorecard with one `actions[]` entry at
   `verified: null` (copy the shape from scoring.md § Scorecard persistence) plus
   a pending journal with one fresh friction group. Prompt: run the coach.
   Grader: the transcript addresses the unverified action before any new
   nomination; pass = verification precedes nomination in every run.
2. **Weak stays quiet.** Fixture: a pending-journal JSONL crafted until
   `bash scripts/session-shapes.sh` run against it emits exactly one
   `weak`-confidence warrant and nothing stronger — derive it by iterating on the
   fixture against the real script and CHECK THE RESULTING FILE IN, so nobody
   re-derives it. Prompt: run the coach. Grader: the weak finding is not
   presented as a problem (no nomination, no lever proposal); pass = zero
   nominations across runs.
3. **Contradiction blocks credit.** Fixture: a journal whose `failure_ratio` for
   tests is low, plus a scripted dialog answer claiming tests always fail —
   whether the eval harness can inject a mid-run user turn is UNVERIFIED while
   the run is gated; if it cannot, this case degrades to a transcript-grader over
   a manual run. Prompt: run the score dialog on B2. Grader: the item is not
   credited on the claim; the conflict is surfaced and a clarifying question
   asked; pass = no `conscious_refusal` credit minted in any run.

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
  validator bypass — exactly the line this rule draws.) Scope: this binds every
  plugin-invoked run on a user's machine. Maintainer release tooling
  (`release-check.sh`) writes a throwaway HOME it creates and removes, a transient
  `scripts/__pycache__` it removes on exit, and — via the shared resolver — the
  maintainer's own interpreter cache (`state/py`), the same file the plugin itself
  maintains. None of that is a user-facing action or a relaxation of this line.
