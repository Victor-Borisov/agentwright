#!/usr/bin/env python3
"""Agentwright score trajectory — turns scorecard history into terminal sparklines.

Read-only: reads ~/.claude/agentwright/scorecard.json and prints a JSON block the
`show` skill renders. Deterministic (the script picks the block glyphs, not the LLM).
Numbers are the truth; the sparkline is illustrative. Exit 0 always.

Emits per series: a unicode sparkline, first/last values, and a trend flag. Friction
is separate because its snapshot (`friction_per_100`) only fills in from the score
runs that recorded it — older history entries won't have it.
"""
import json
import os
import sys

CARD = os.path.join(os.path.expanduser("~"), ".claude", "agentwright", "scorecard.json")
BLOCKS = "▁▂▃▄▅▆▇█"
MAX_POINTS = 20  # keep sparklines short enough for a terminal / screen-share


def spark(values):
    vals = [v for v in values if isinstance(v, (int, float))]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return "▄" * len(vals)
    return "".join(BLOCKS[min(7, int((v - lo) / (hi - lo) * 7 + 0.5))] for v in vals)


def trend(first, last, rise):
    """rise = the minimum delta that counts as movement (else flat)."""
    if first is None or last is None:
        return None
    d = last - first
    eps = 1e-9  # so an exactly-threshold delta (0.6-0.5 float dust) reads consistently
    if d >= rise - eps:
        return "rising"
    if d <= -rise + eps:
        return "falling"
    return "flat"


def series(history, key):
    """Ordered numeric values for a top-level history key, entries that have it."""
    return [h[key] for h in history if isinstance(h.get(key), (int, float))]


def axis_series(history, axis):
    out = []
    for h in history:
        ax = h.get("axes")
        if isinstance(ax, dict) and isinstance(ax.get(axis), (int, float)):
            out.append(ax[axis])
    return out


def line(values, rise):
    if len(values) < 2:
        return None
    return {"spark": spark(values), "first": values[0], "last": values[-1],
            "trend": trend(values[0], values[-1], rise)}


def main():
    try:
        with open(CARD, encoding="utf-8") as f:
            card = json.load(f)
    except (OSError, ValueError):
        print(json.dumps({"runs": 0}))
        return

    history = card.get("history", []) or []
    history = history[-MAX_POINTS:]
    runs = len(history)

    out = {"runs": runs}
    if runs < 2:
        out["note"] = "single_run" if runs == 1 else "no_runs"
        # fixes tally is still meaningful on a single run
        out["fixes"] = fixes_tally(card)
        print(json.dumps(out, ensure_ascii=False))
        return

    out["score"] = line(series(history, "score"), rise=3)  # ±3 precision band

    fr = series(history, "friction_per_100")
    out["friction"] = (line(fr, rise=0.5) or {}) if len(fr) >= 2 else {"available": False}
    if isinstance(out["friction"], dict) and out["friction"].get("trend"):
        out["friction"]["available"] = True
        out["friction"]["runs_with_data"] = len(fr)
        # for friction, falling is GOOD — annotate direction plainly
        out["friction"]["good"] = out["friction"]["trend"] == "falling"

    axes = {}
    for ax in ("landscape", "judgment", "oversight", "outcome"):
        ln = line(axis_series(history, ax), rise=0.1)
        if ln:
            axes[ax] = ln
    if axes:
        out["axes"] = axes

    out["fixes"] = fixes_tally(card)
    print(json.dumps(out, ensure_ascii=False))


def fixes_tally(card):
    actions = card.get("actions", []) or []
    verified = sum(1 for a in actions if a.get("verified") is True)
    awaiting = sum(1 for a in actions if a.get("verified") is None)
    failed = sum(1 for a in actions if a.get("verified") is False)
    return {"verified": verified, "awaiting": awaiting, "failed": failed}


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never break the show flow
        print(json.dumps({"runs": 0, "error": str(exc)}))
    sys.exit(0)
