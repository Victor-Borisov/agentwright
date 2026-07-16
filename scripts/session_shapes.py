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

# tool_use tool labels → capability the user demonstrably reached for
CAP_MAP = {
    "EnterPlanMode": "plan_mode", "ExitPlanMode": "plan_mode",
    "EnterWorktree": "worktree", "ExitWorktree": "worktree",
    "Task": "subagent", "Agent": "subagent",
    "mcp": "mcp", "WebSearch": "web", "WebFetch": "web", "LSP": "lsp",
}
ALL_CAPS = ("plan_mode", "subagent", "worktree", "mcp", "web", "lsp")
HIGH_TURN = 40  # session size that warrants subagent/plan-mode nomination
THRASH_MIN_FAILS = 3     # a category needs this many failures to count as "stuck"
THRASH_RATIO = 0.6       # failures/(failures+successes) above this = going in circles
STRONG_MIN_SESSIONS = 2  # recurs in >=2 sessions = a cross-session pattern (strong)
CONTRADICT_RATIO = 0.3   # a "keeps failing" claim below this ratio is contradicted (LLM layer)


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
    fail_cat = {}     # tool_failure by category
    ok_cat = {}       # tool_success by category (the failure-ratio denominator)
    caps = set()      # capabilities demonstrably used this session
    effort = ""
    pmode = ""
    for e in entries:
        ev = str(e.get("event", "unknown"))
        counts[ev] = counts.get(ev, 0) + 1
        cat = str(e.get("category", "")) if e.get("category") else ""
        if ev == "tool_failure" and cat:
            fail_cat[cat] = fail_cat.get(cat, 0) + 1
        elif ev == "tool_success" and cat:
            ok_cat[cat] = ok_cat.get(cat, 0) + 1
        elif ev == "tool_use":
            lab = CAP_MAP.get(str(e.get("tool", "")))
            if lab:
                caps.add(lab)
        elif ev == "session_start":
            if e.get("effort"):
                effort = str(e["effort"])
            if e.get("pmode"):
                pmode = str(e["pmode"])

    categories = fail_cat  # back-compat name used below (bursts, output)
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
        "failure_categories": fail_cat,
        "success_categories": ok_cat,
        "capabilities_used": sorted(caps),
        "effort": effort,
        "pmode": pmode,
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

    # ---- capability coverage: did the user reach for each lever at all? ----
    cap_sessions = {c: 0 for c in ALL_CAPS}
    for s in shapes:
        for c in s["capabilities_used"]:
            cap_sessions[c] = cap_sessions.get(c, 0) + 1
    capabilities = {c: {"used": cap_sessions[c] > 0, "sessions": cap_sessions[c]} for c in ALL_CAPS}

    # ---- failure ratio + per-category recurrence (busy day != bad day) ----
    fail_tot, ok_tot, cat_sessions = {}, {}, {}
    for s in shapes:
        for cat, n in s["failure_categories"].items():
            fail_tot[cat] = fail_tot.get(cat, 0) + n
            cat_sessions[cat] = cat_sessions.get(cat, 0) + 1  # sessions where cat failed
        for cat, n in s["success_categories"].items():
            ok_tot[cat] = ok_tot.get(cat, 0) + n
    failure_ratio = {}
    for cat in set(fail_tot) | set(ok_tot):
        f, o = fail_tot.get(cat, 0), ok_tot.get(cat, 0)
        failure_ratio[cat] = {
            "failures": f, "successes": o,
            "ratio": round(f / (f + o), 2) if (f + o) else None,
        }

    # ---- confidence grade per failing category (evidence density) ----
    # strong: recurs in >=2 sessions AND stuck (ratio>=0.6). medium: recurs in >=2,
    # OR one session but clearly stuck. weak: single/low-ratio (may be a busy day).
    # The coach may UPGRADE one tier when a /log note corroborates (semantic, not here).
    friction_confidence = {}
    for cat in fail_tot:
        n = cat_sessions.get(cat, 0)
        r = failure_ratio[cat]["ratio"]
        rr = r if r is not None else 1.0
        f = fail_tot[cat]
        if n >= STRONG_MIN_SESSIONS and rr >= THRASH_RATIO:
            friction_confidence[cat] = "strong"
        elif n >= STRONG_MIN_SESSIONS or (n == 1 and f >= THRASH_MIN_FAILS and rr >= THRASH_RATIO):
            friction_confidence[cat] = "medium"
        else:
            friction_confidence[cat] = "weak"

    # ---- effort + permission-mode distribution across sessions ----
    effort_dist = {}
    pmode_dist = {}
    for s in shapes:
        if s.get("effort"):
            effort_dist[s["effort"]] = effort_dist.get(s["effort"], 0) + 1
        if s.get("pmode"):
            pmode_dist[s["pmode"]] = pmode_dist.get(s["pmode"], 0) + 1

    # ---- thrash detection: sessions that went in circles (feeds /retro) ----
    # SHAPE only — never a read of prompt quality. A session looks stuck when it
    # burst-failed, OR was large AND a category kept failing (high ratio, >=3 fails).
    # Compactions strengthen the read but never trigger alone (lunch breaks compact).
    thrash_sessions = []
    for s in shapes:
        turns = s["events"].get("turn", 0)
        compacts = s["events"].get("compact", 0)
        bursts = s["failure_bursts"]
        worst = None
        for cat, f in s["failure_categories"].items():
            if f < THRASH_MIN_FAILS:
                continue
            o = s["success_categories"].get(cat, 0)
            r = f / (f + o)
            if r >= THRASH_RATIO and (worst is None or r > worst["ratio"]):
                worst = {"category": cat, "failures": f, "successes": o, "ratio": round(r, 2)}
        if bursts or (turns >= HIGH_TURN and worst):
            if bursts and worst and compacts >= 1:
                conf = "strong"
            elif bursts or (worst and compacts >= 1):
                conf = "medium"
            else:
                conf = "weak"
            thrash_sessions.append({
                "session": s["session"], "projects": s["projects"],
                "turns": turns, "compacts": compacts, "confidence": conf,
                "bursts": bursts, "stuck_category": worst,
            })
    thrash_names = {t["session"] for t in thrash_sessions}

    # ---- warrant + absence: situations that called for a lever not used ----
    # Nominations only — the coach still asks; never convict. Each carries a
    # confidence grade so the coach can order (strong first) and hold weak ones.
    warrants = []
    # habitual bypass is an S3 symptom to ASK about (may be a conscious container choice)
    bypass = pmode_dist.get("bypassPermissions", 0)
    if bypass:
        warrants.append({"lever": "permission_tuning", "reason": "habitual_bypass",
                         "bypass_sessions": bypass, "total_sessions": len(shapes),
                         "confidence": "strong" if bypass == len(shapes) else "medium"})
    big = [s for s in shapes if s["events"].get("turn", 0) >= HIGH_TURN]
    if big and not capabilities["subagent"]["used"]:
        conf = "medium" if any(s["events"].get("compact", 0) >= 2 for s in big) else "weak"
        warrants.append({"lever": "subagent", "reason": "high_turn_sessions",
                         "sessions": [s["session"] for s in big], "confidence": conf})
    if overlaps and not capabilities["worktree"]["used"]:
        warrants.append({"lever": "worktree", "reason": "same_repo_overlap",
                         "overlaps": len(overlaps),
                         "confidence": "strong" if len(overlaps) >= 2 else "medium"})
    if big and not capabilities["plan_mode"]["used"]:
        conf = "medium" if any(s["session"] in thrash_names for s in big) else "weak"
        warrants.append({"lever": "plan_mode", "reason": "large_session_no_plan",
                         "sessions": [s["session"] for s in big], "confidence": conf})
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
        "capabilities": capabilities,
        "failure_ratio": failure_ratio,
        "friction_confidence": friction_confidence,
        "category_sessions": cat_sessions,
        "effort_distribution": effort_dist,
        "pmode_distribution": pmode_dist,
        "unused_lever_warrants": warrants,
        "thrash_sessions": thrash_sessions,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
    sys.exit(0)
