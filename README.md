# Agentwright — harness maturity score & coach for Claude Code

**Not tokens burned — harness maturity.** Agentwright measures how well you *work
with* Claude Code, not how much you spend on it: do you know the landscape of levers
(rules, hooks, gates, MCP, subagents), do you pick the right one for a real friction,
do you review the artifacts that deserve review — and does your setup actually reduce
friction over time.

Your **Agentwright Score (1–100)** is a self-race: it moves between runs, can fall,
and always explains why. Top band: **Agent Architect**.

## What it does

- **Friction journal** — the plugin's own hooks quietly log minimal signals: Bash
  tool failures with a locally derived category (test / lint / build / install / git /
  other), permission prompts and denials, context compactions, and turn/session
  markers as activity denominators. Only event kind, tool name, category, project name
  and timestamp are stored — never command text, prompts, or outputs.
- **`/agentwright:log`** — capture a friction note in your own words the moment
  something annoys you; the highest-signal input for the next review.
- **Morning reminder** — a fast SessionStart check: if unreviewed friction accumulated
  since your last review, you get one line suggesting `/agentwright:coach`. Silent
  otherwise.
- **`/agentwright:coach`** — the closed loop: ① verify that past fixes actually
  reduced friction (rates per 100 turns of activity, not raw counts) → ② group fresh
  frictions by root cause *and nominate missed opportunities from session shapes*
  (a 7-hour two-wave session → "was that two tasks? here's session splitting";
  overlapping sessions in one repo → worktrees) → ③ ask *your* judgment first →
  ④ compare with its pick → ⑤ apply the fix safely from a vetted lever library
  (harness-embedded changes are proof-tested and reviewed; cheap ones just applied)
  → ⑥ record for next verification. Opportunity answers are remembered — a conscious
  "no" is never re-asked.
- **`/agentwright:score`** — deterministic artifact scan + a short situational dialog
  → checklist with three-way credit (*present / conscious refusal / absent*), security
  gate, auditable 1–100 score, growth plan tied to specific free Anthropic Academy
  modules. Launching from a multi-repo workspace root? The scanner finds every git
  repo one level down and scores each separately (GitHub or GitLab CI alike);
  personal non-git folders are left alone.

- **`/agentwright:show`** — display the saved score instantly (screen-share friendly):
  headline, axes, per-project lines, trend. Read-only, no recomputation. The card is
  integrity-sealed on every score run; a scorecard edited outside Agentwright is
  refused, not displayed. (Tamper-evidence for casual edits — the score stays
  self-assessed and says so on every card.)

A deliberate "no" counts. If you don't use a lever and can explain the tradeoff that
rules it out in your context, you get full credit — seniority is *closed consciously*,
not *everything installed*.

## Privacy

Everything is local. The plugin **never** reads Claude conversation transcripts,
chat history, `/insights` data, or `~/.claude/usage-data/` — by design, per the
[Anthropic Software Directory Policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy).
Signals come only from its own hooks (minimal metadata) and user-authored artifacts
(settings, CLAUDE.md, hooks, skills, MCP configs, repo state). Nothing is transmitted
anywhere.

Full documentation: [victor-borisov.github.io/agentwright](https://victor-borisov.github.io/agentwright/)
(English) · [Russian version](https://victor-borisov.github.io/agentwright/index.ru.html)
(sources in [docs/](docs/)).

## Quickstart

Requirements: Claude Code, `bash`, `python3` (`git` and `gitleaks` improve probes).

**1. Install** — inside Claude Code, run:

```
/plugin marketplace add Victor-Borisov/agentwright
/plugin install agentwright@agentwright
```

(For local development instead: `claude --plugin-dir /path/to/agentwright`.)

**Stay current — enable auto-update once:** `/plugin` → *Marketplaces* → select
*agentwright* → *Enable auto-update*. New versions then arrive on session start
(you'll be prompted to `/reload-plugins`); otherwise run `/plugin marketplace update
agentwright` yourself when you want the latest. After an update lands, the plugin
prints a one-line "updated to vX — what changed" note.

**2. Get your baseline** — run `/agentwright:score`. A short dialog (~10 min) plus
a deterministic scan of your setup produces your first score and a growth plan.
The first run sticks to core items; effect-over-time items enter from run two.

**3. Just work.** The plugin journals friction quietly (categories and counters
only — never your commands or prompts). When something annoys you, capture it in
your own words with `/agentwright:log` — that's the highest-signal input.

**4. When the morning reminder fires** (friction accumulated), run
`/agentwright:coach`: it verifies whether past fixes actually reduced friction,
groups new frictions by root cause, asks your judgment first, then applies a fix
from the vetted lever library and records it for the next verification.

**5. Re-run `/agentwright:score`** after a couple of weeks — the score moves, and
the report always explains why.

The first `/agentwright:score` or `/agentwright:coach` asks which language the
plugin should speak with you (any language works) and remembers the choice in
`config.json`; artifacts (scorecard, journal) stay English.

Data lives in `~/.claude/agentwright/` (journal, flags, scorecard, archive, state,
config).
Delete that directory to reset everything. Curious where you are in the loop?
`python3 scripts/product_metrics.py` prints your local funnel.

Optional: show your score in the statusline — see `scripts/statusline-example.sh`.

## Keeping up with Claude Code

Claude Code grows fast; Agentwright is built for that. The knowledge base
(checklist, levers, opportunities) is versioned and calibrated against a specific
Claude Code release — when yours is newer, the plugin says so once and the score
report treats missing new capabilities as "the bar moved", never as your
regression. Maintainers: see `MAINTAINING.md` and `/agentwright:refresh`.

Agentwright is an independent tool **for Claude Code**. Not affiliated with,
sponsored, or endorsed by Anthropic. Claude is a trademark of Anthropic, PBC.

## License

MIT
