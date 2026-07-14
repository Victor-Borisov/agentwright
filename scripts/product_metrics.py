#!/usr/bin/env python3
"""Agentwright product funnel — computed locally, printed locally, sent nowhere.

Answers "is the plugin itself working as a product?" for THIS machine:

  installed  -> journal collecting     (hooks produce events)
  activated  -> first /score baseline  (scorecard history exists)
  in loop    -> coach reviews happen   (flags/reviewed-*, actions recorded)
  core value -> a fix VERIFIED to cut friction (actions[].verified == true)
  retained   -> loop still alive in the trailing 28 days

Output is dates and counts only — no commands, prompts, or file paths — so it is
safe to paste into a feedback issue if you choose to share it. Nothing is
transmitted by this script or any other part of the plugin.

Usage: product_metrics.py [--json]
"""
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.expanduser("~"), ".claude", "agentwright")


def parse_ts(ts):
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(ts, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def journal_events():
    """Yield (datetime, event_kind) for every journal line, pending + archive."""
    for sub in ("pending", "archive"):
        for path in sorted(glob.glob(os.path.join(DATA_DIR, sub, "*.jsonl"))):
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                        except ValueError:
                            continue
                        dt = parse_ts(rec.get("ts", ""))
                        if dt:
                            yield dt, rec.get("event", "")
            except OSError:
                continue


def load_scorecard():
    try:
        with open(os.path.join(DATA_DIR, "scorecard.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def review_dates():
    dates = []
    for path in glob.glob(os.path.join(DATA_DIR, "flags", "reviewed-*")):
        day = os.path.basename(path)[len("reviewed-"):][:10]
        try:
            dates.append(datetime.strptime(day, "%Y-%m-%d").date())
        except ValueError:
            continue
    return sorted(dates)


def main():
    now = datetime.now(timezone.utc)
    events = sorted(journal_events())
    card = load_scorecard() or {}
    reviews = review_dates()
    history = card.get("history", [])
    actions = card.get("actions", [])

    first_event = events[0][0] if events else None
    last_event = events[-1][0] if events else None
    first_score = history[0].get("date") if history else None
    verified_dates = sorted(a.get("date", "") for a in actions if a.get("verified") is True)
    d7 = now - timedelta(days=7)
    d28 = now - timedelta(days=28)
    reviews_28d = [d for d in reviews if d >= d28.date()]

    funnel = {
        "installed_collecting": {
            "reached": bool(events),
            "first_event": first_event.strftime("%Y-%m-%d") if first_event else None,
            "events_total": len(events),
        },
        "activated_first_score": {
            "reached": bool(first_score),
            "date": first_score,
            "score_runs": len(history),
        },
        "in_the_loop": {
            "reached": bool(reviews or actions),
            "coach_reviews": len(reviews),
            "actions_recorded": len(actions),
            "actions_awaiting_verification": sum(1 for a in actions if a.get("verified") is None),
        },
        "core_value_verified_fix": {
            "reached": bool(verified_dates),
            "first_verified": verified_dates[0] if verified_dates else None,
            "verified_total": len(verified_dates),
        },
        "retained_28d": {
            "reached": bool(last_event and last_event >= d28) and bool(reviews_28d),
            "events_last_7d": sum(1 for dt, _ in events if dt >= d7),
            "events_last_28d": sum(1 for dt, _ in events if dt >= d28),
            "coach_reviews_last_28d": len(reviews_28d),
        },
    }

    if "--json" in sys.argv:
        print(json.dumps(funnel, indent=2))
        return

    labels = {
        "installed_collecting": "1. Installed & collecting",
        "activated_first_score": "2. Activated (first /score)",
        "in_the_loop": "3. In the loop (/coach)",
        "core_value_verified_fix": "4. Core value (verified fix)",
        "retained_28d": "5. Retained (28d)",
    }
    print("Agentwright product funnel (local only, nothing transmitted)\n")
    blocked = False
    for key, label in labels.items():
        st = funnel[key]
        mark = "x" if st.pop("reached") else " "
        detail = ", ".join("%s: %s" % (k, v) for k, v in st.items() if v not in (None, 0))
        print("[%s] %-30s %s" % (mark, label, detail or "-"))
        if mark == " " and not blocked:
            blocked = True
            hints = {
                "installed_collecting": "hooks produced no events yet — work a session, then re-run",
                "activated_first_score": "run /agentwright:score to set your baseline",
                "in_the_loop": "run /agentwright:coach after friction accumulates",
                "core_value_verified_fix": "a recorded fix has not yet passed two-part verification — keep working, the coach checks on each run",
                "retained_28d": "no activity in the last 28 days",
            }
            print("    ^ next: %s" % hints[key])


if __name__ == "__main__":
    main()
