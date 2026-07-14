#!/usr/bin/env python3
"""Agentwright session-shape analyzer (deterministic layer for the coach).

Reads the plugin's own journal files (pending/, plus archive/ with --archive)
and prints per-session shapes + cross-session overlaps as JSON. The LLM layer
interprets shapes against references/opportunities.md; it must not re-derive
them from raw lines.

Sessions are keyed by the SESSION suffix of the filename (not the date), so a
session crossing midnight stays one session. The `manual` stream (notes from
/agentwright:log) is NOT a session: its notes are reported separately and are
excluded from session counts, overlaps, and wave math.

Usage: session_shapes.py [--archive] [--days N]   (default: pending only, 14 days)

Stdlib only (Python 3.8+). Exit code always 0; problems reported inside the JSON.
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.expanduser("~/.claude/agentwright")
WAVE_GAP_MIN = 45          # a pause >= this long splits activity into waves
BURST_WINDOW_MIN = 15      # window for same-category failure bursts
BURST_MIN_FAILURES = 3
FRICTION_EVENTS = {"tool_failure", "permission_denied", "compact", "manual"}
FNAME_RE = re.compile(r"^pending-\d{4}-\d{2}-\d{2}-(?P<suffix>.+)\.jsonl$")


def parse_ts(value):
    """Accept both legacy UTC ('...Z') and local-offset ('...+0300') stamps."""
    value = str(value)
    try:
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        return None


def load_streams(include_archive, days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    dirs = [os.path.join(DATA_DIR, "pending")]
    if include_archive:
        dirs.append(os.path.join(DATA_DIR, "archive"))
    sessions = {}
    manual = []
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "pending-*.jsonl"))):
            m = FNAME_RE.match(os.path.basename(path))
            suffix = m.group("suffix") if m else "unknown"
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                        except Exception:
                            continue
                        ts = parse_ts(entry.get("ts", ""))
                        if ts is None or ts < cutoff:
                            continue
                        entry = {**entry, "_ts": ts}
                        if suffix == "manual" or entry.get("event") == "manual":
                            manual.append(entry)
                        else:
                            sessions.setdefault(suffix, []).append(entry)
            except Exception:
                continue
    return sessions, manual


def shape_of(key, entries):
    entries.sort(key=lambda e: e["_ts"])
    times = [e["_ts"] for e in entries]
    turns = [e["_ts"] for e in entries if e.get("event") == "turn"]

    waves = 1
    activity = turns or times
    for prev, cur in zip(activity, activity[1:]):
        if (cur - prev) >= timedelta(minutes=WAVE_GAP_MIN):
            waves += 1

    counts = {}
    categories = {}
    for e in entries:
        ev = str(e.get("event", "unknown"))
        counts[ev] = counts.get(ev, 0) + 1
        if e.get("category"):
            categories[str(e["category"])] = categories.get(str(e["category"]), 0) + 1

    bursts = []
    for cat in categories:
        fails = [e["_ts"] for e in entries
                 if e.get("event") == "tool_failure" and e.get("category") == cat]
        for i in range(len(fails) - BURST_MIN_FAILURES + 1):
            span = fails[i + BURST_MIN_FAILURES - 1] - fails[i]
            if span <= timedelta(minutes=BURST_WINDOW_MIN):
                bursts.append({"category": cat, "failures": BURST_MIN_FAILURES,
                               "within_minutes": round(span.total_seconds() / 60, 1)})
                break

    projects = sorted({str(e.get("project", "unknown")) for e in entries})

    return {
        "session": key,
        "projects": projects,
        "start": times[0].astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "end": times[-1].astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "duration_minutes": round((times[-1] - times[0]).total_seconds() / 60, 1),
        "activity_waves": waves,
        "events": counts,
        "failure_categories": categories,
        "failure_bursts": bursts,
        "friction_events": sum(n for ev, n in counts.items() if ev in FRICTION_EVENTS),
        "_start": times[0], "_end": times[-1],
    }


def find_overlaps(shapes):
    overlaps = []
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            a, b = shapes[i], shapes[j]
            common = set(a["projects"]) & set(b["projects"])
            if not common:
                continue
            start = max(a["_start"], b["_start"])
            end = min(a["_end"], b["_end"])
            if start < end:
                overlaps.append({
                    "sessions": [a["session"], b["session"]],
                    "projects": sorted(common),
                    "overlap_minutes": round((end - start).total_seconds() / 60, 1),
                })
    return overlaps


def main():
    include_archive = "--archive" in sys.argv
    days = 14
    if "--days" in sys.argv:
        try:
            days = max(1, int(sys.argv[sys.argv.index("--days") + 1]))
        except Exception:
            pass

    sessions, manual = load_streams(include_archive, days)
    shapes = [shape_of(k, v) for k, v in sorted(sessions.items()) if v]
    overlaps = find_overlaps(shapes)
    for s in shapes:
        s.pop("_start", None)
        s.pop("_end", None)

    manual.sort(key=lambda e: e["_ts"])
    manual_notes = [{
        "ts": e["_ts"].astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project": str(e.get("project", "unknown")),
        "note": str(e.get("note", "")),
    } for e in manual if e.get("note")]

    active = [s for s in shapes if s["events"].get("turn", 0) > 0 or s["friction_events"] > 0]
    total_friction = sum(s["friction_events"] for s in shapes) + len(manual_notes)
    total_turns = sum(s["events"].get("turn", 0) for s in shapes)
    print(json.dumps({
        "window_days": days,
        "sessions": shapes,
        "overlaps": overlaps,
        "manual_notes": manual_notes,
        "totals": {
            "session_count": len(shapes),
            "active_session_count": len(active) or len(shapes),
            "turns": total_turns,
            "friction_events": total_friction,
            # Primary normalization: per 100 turns. Turn count is stationary;
            # session count is NOT (the coach itself teaches session splitting,
            # which multiplies sessions and would deflate per-session rates).
            "friction_per_100_turns":
                round(100.0 * total_friction / total_turns, 2) if total_turns else None,
            "friction_per_active_session":
                round(total_friction / (len(active) or len(shapes) or 1), 2),
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
    sys.exit(0)
