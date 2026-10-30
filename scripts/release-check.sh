#!/usr/bin/env bash
# Release checks for this plugin — the executable form of MAINTAINING § Testing
# before release. Run from anywhere:
#
#   bash scripts/release-check.sh
#
# Exit 0 — every check passed. Exit 1 — at least one failed; each failure names the
# file or value that caused it. The script publishes nothing and touches no network.
# Writes: a throwaway HOME (removed on exit via trap), a transient scripts/__pycache__
# (same), and — via sourcing py-resolve.sh in step 0 — possibly the maintainer's own
# interpreter cache (state/py), the same file the plugin itself maintains.
#
# Design rules learned from this file's own review history (two drafts shipped
# detectors that could never fire, each printing `ok`):
# — Every detector in the guard block carries a POSITIVE CONTROL: before scanning
#   the tree it must flag a planted bad sample, otherwise the check reports its own
#   breakage instead of a silent pass. A guard that cannot fail is decoration.
# — Text guards run in python, not `grep -P`: PCRE `\x{}` escapes above 0xFF fail
#   to compile without a UTF locale (exit 2), and `|| true` turns that into a pass.
# — The scanned file list is fetched inside the guard process (a heredoc consumes
#   the stdin a pipe would have carried) and includes UNTRACKED files, so the gate
#   covers new files before `git add`, with a floor on files actually read.

set -u
cd "$(dirname "$0")/.." || exit 1

FAILED=0
pass() { printf 'ok    %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAILED=1; }
note() { printf '      %s\n' "$1"; }

FH=""
cleanup() {
  [ -n "$FH" ] && rm -rf "$FH"
  rm -rf scripts/__pycache__
}
trap cleanup EXIT

# --- 0. interpreter (same resolver the wrappers use) --------------------------

. scripts/py-resolve.sh
if [ -z "$PY" ]; then
  printf 'FAIL  no runnable python 3.8+ found — nothing else can be checked\n'
  exit 1
fi
note "interpreter: $PY"

# --- 1. syntax ----------------------------------------------------------------

bad=""
for f in scripts/*.sh; do
  bash -n "$f" 2>/dev/null || bad="$bad $f"
done
[ -z "$bad" ] && pass "shell syntax" || fail "shell syntax:$bad"

if "$PY" -m py_compile scripts/*.py >/dev/null 2>&1; then
  pass "python syntax"
else
  fail "python syntax (run: $PY -m py_compile scripts/*.py)"
fi

if "$PY" - <<'PYEOF' >/dev/null 2>&1
import json
for path in (
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "hooks/hooks.json",
    "references/calibration.json",
):
    with open(path, encoding="utf-8") as f:
        json.load(f)
PYEOF
then
  pass "json parses (plugin, marketplace, hooks, calibration)"
else
  fail "json does not parse in one of: plugin.json marketplace.json hooks.json calibration.json"
fi

# --- 2. manifest pair agreement (versioning contract) ---------------------------

pair="$("$PY" - <<'PYEOF' 2>/dev/null
import json

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

plugin = load(".claude-plugin/plugin.json")
market = load(".claude-plugin/marketplace.json")
entries = [p for p in market.get("plugins", []) if p.get("name") == plugin.get("name")]
if not entries:
    print("MISMATCH no marketplace entry named %s" % plugin.get("name"))
elif entries[0].get("version") != plugin.get("version"):
    print("MISMATCH plugin %s vs marketplace %s" % (plugin.get("version"), entries[0].get("version")))
else:
    print("OK %s %s" % (plugin.get("name"), plugin.get("version")))
PYEOF
)"
case "$pair" in
  OK*) pass "manifest pair agrees (${pair#OK })" ;;
  *)   fail "manifest pair: ${pair:-unreadable}" ;;
esac

# --- 3. text guards + invocation guard + wrapper integrity + contract canaries --
# All in one python process: portable regexes, positive controls, and a file list
# fetched via subprocess (tracked AND untracked) with a floor on files actually read.

guards="$("$PY" - <<'PYEOF'
import re
import subprocess

failures = []

# ---- detectors -------------------------------------------------------------

CYRILLIC = re.compile("[\u0400-\u04FF]")
# Built by concatenation so this file never matches its own source.
VOUCH = re.compile("(" + "hon" + "est" + "|" + "\u0447\u0435\u0441\u0442\u043d" + ")", re.IGNORECASE)

VAR_RE = r"\$\{?CLAUDE_PLUGIN_ROOT\}?"
OCC = re.compile(VAR_RE + r'[\\"\x27]*/scripts/')
# Only bash may prefix a plugin-script call: every entry point is a .sh wrapper now,
# so a python3-prefixed .py call is itself the regression being guarded against.
INTERP = re.compile(r'bash[\s\\"\x27]*$')

def bare_invocations(text):
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for m in OCC.finditer(line):
            prefix = line[: m.start()].rstrip()
            if not INTERP.search(prefix[-24:] if len(prefix) > 24 else prefix):
                hits.append((line_no, line.strip()[:120]))
    return hits

# Interpreter lookup/invocation forms forbidden outside py-resolve.sh. Words like
# "python" inside messages are fine; command-position and lookup forms are not.
LOOKUP_FORMS = [
    re.compile(r"command\s+-v\s+python"),
    re.compile(r"\bwhich\s+python"),
    re.compile(r"\btype\s+-p\s+python"),
    re.compile(r"(?:^|[;&|]|\$\(|`)\s*(?:exec\s+)?python3?\b"),
]

def wrapper_violations(text):
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        code = line.strip()
        if code.startswith("#"):
            continue
        for pat in LOOKUP_FORMS:
            if pat.search(code):
                hits.append((line_no, code[:120]))
                break
    return hits

# ---- positive controls: a detector that cannot fire fails the run -----------

if not CYRILLIC.search("\u043f\u0440\u0438\u0432\u0435\u0442"):
    failures.append("SELFTEST language detector does not fire on a Cyrillic sample")
if CYRILLIC.search("plain ascii text"):
    failures.append("SELFTEST language detector fires on ascii")
if not VOUCH.search("to be " + "hon" + "est, it works"):
    failures.append("SELFTEST style detector does not fire on a vouching sample")
if VOUCH.search("state the fact plainly"):
    failures.append("SELFTEST style detector fires on clean text")

BRACED = "${" + "CLAUDE_PLUGIN_ROOT" + "}"
UNBRACED = "$" + "CLAUDE_PLUGIN_ROOT"
bad1 = '"command": "bash \\"' + BRACED + '\\"/scripts/a.sh; \\"' + BRACED + '\\"/scripts/b.sh x"'
bad2 = "Run in bash this command: `" + BRACED + "/scripts/scan-artifacts.sh`"
bad3 = "Run: `" + UNBRACED + "/scripts/session-shapes.sh --archive`"
bad4 = "run `python3 " + BRACED + "/scripts/session_shapes.py` and store"
good = 'bash "' + BRACED + '"/scripts/x.sh and `bash ' + BRACED + "/scripts/y.sh --flag`"
if len(bare_invocations(bad1)) != 1:
    failures.append("SELFTEST invocation detector misses a chained bare call")
if len(bare_invocations(bad2)) != 1:
    failures.append("SELFTEST invocation detector misses a prose bare call")
if len(bare_invocations(bad3)) != 1:
    failures.append("SELFTEST invocation detector misses the unbraced variable form")
if len(bare_invocations(bad4)) != 1:
    failures.append("SELFTEST invocation detector blesses a python3-prefixed call")
if bare_invocations(good):
    failures.append("SELFTEST invocation detector flags bash-prefixed calls")

wbad1 = 'PY="$(' + "command -v " + 'python3 || true)"'
wbad2 = "exec " + "python3" + ' "${DIR}/x.py" "$@"'
wbad3 = 'PY="$(' + "which " + 'python3)"'
wgood = 'echo "agentwright: no runnable python 3.8+ found" >&2'
if not wrapper_violations(wbad1):
    failures.append("SELFTEST wrapper detector misses a command -v lookup")
if not wrapper_violations(wbad2):
    failures.append("SELFTEST wrapper detector misses a bare exec python3")
if not wrapper_violations(wbad3):
    failures.append("SELFTEST wrapper detector misses a which lookup")
if wrapper_violations(wgood):
    failures.append("SELFTEST wrapper detector fires on a plain message string")

# ---- collect the file list (tracked + untracked, floor on files read) --------
# Fetched here, not piped in: `cmd | python - <<EOF` silently feeds python the
# heredoc instead of the pipe, and an empty list turns every guard below into a
# vacuous pass — that exact defect shipped in a prior draft of this file.

def ls(args):
    r = subprocess.run(["git", "ls-files", "-z"] + args, capture_output=True, text=True)
    return r.returncode, [f for f in r.stdout.split("\0") if f]

rc1, tracked = ls([])
rc2, untracked = ls(["--others", "--exclude-standard"])
files = sorted(set(tracked) | set(untracked))
if rc1 != 0 or rc2 != 0:
    failures.append("GUARD git ls-files failed (rc %d/%d) — guards scanned nothing" % (rc1, rc2))

TEXT_EXT = (".md", ".sh", ".py", ".json", ".html", ".yml", ".yaml", ".txt")
opened = 0
texts = {}
for path in files:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        continue
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        if path.endswith(TEXT_EXT):
            failures.append("ENCODING %s is not valid utf-8 — text guards cannot scan it, fix the file" % path)
        continue
    opened += 1
    texts[path] = text

if opened < 20:
    failures.append("GUARD only %d files were actually read — guards scanned almost nothing" % opened)

# ---- scan -------------------------------------------------------------------

for path, text in texts.items():
    if path.endswith(".ru.html"):
        continue  # sanctioned translation — the one exclusion for the language guard
    if CYRILLIC.search(text):
        failures.append("LANGUAGE non-English content in %s" % path)
    m = VOUCH.search(text)
    if m:
        failures.append("STYLE vouching wording in %s (%r)" % (path, m.group(0)))

inv_scope = ["hooks/hooks.json", "README.md"] + [f for f in texts if f.startswith("skills/")]
for path in inv_scope:
    text = texts.get(path)
    if text is None:
        continue
    for line_no, snippet in bare_invocations(text):
        failures.append("INVOCATION bare or non-bash script call %s:%d: %s" % (path, line_no, snippet))

# Wrapper integrity: any scripts/*.sh that touches $PY or a .py must source
# py-resolve.sh, and no scripts/*.sh may look up or invoke python itself.
for path, text in texts.items():
    if not (path.startswith("scripts/") and path.endswith(".sh")):
        continue
    if path.endswith(("py-resolve.sh", "release-check.sh")):
        continue
    uses_py = ('"$PY"' in text) or re.search(r"\.py\b", text)
    if uses_py and "py-resolve.sh" not in text:
        failures.append("WRAPPER %s runs python work but does not source py-resolve.sh" % path)
    for line_no, snippet in wrapper_violations(text):
        failures.append("WRAPPER %s:%d names or looks up an interpreter itself: %s" % (path, line_no, snippet))

# ---- contract canaries: load-bearing prose that must not be edited away ------

try:
    coach = texts["skills/coach/SKILL.md"]
except KeyError:
    failures.append("CANARY skills/coach/SKILL.md is missing or unreadable")
else:
    i0, i1 = coach.find("## Step 0"), coach.find("## Step 1")
    if not (0 <= i0 < i1):
        failures.append("CANARY coach Step 0 no longer precedes Step 1")
    for literal, label in [
        ("never nominate a `weak` finding as a problem", "weak-finding suppression"),
        ("apply CONTRADICTION", "journal-contradiction rule"),
    ]:
        if literal not in coach:
            failures.append("CANARY coach contract missing: %s" % label)

for line in failures:
    print(line)
PYEOF
)"
guards_rc=$?
if [ "$guards_rc" -ne 0 ]; then
  fail "guard block itself crashed (rc=$guards_rc) — treat as a failed release"
elif [ -z "$guards" ]; then
  pass "language guard (tracked+untracked text is English; translation excluded; undecodable text files fail)"
  pass "style guard (no vouching wording)"
  pass "invocation guard (every \${CLAUDE_PLUGIN_ROOT} script call is bash-wrapper-prefixed; self-tested, both variable forms)"
  pass "wrapper integrity (python work goes through py-resolve.sh; no lookup or direct interpreter call; self-tested)"
  pass "contract canaries (coach step order, weak-finding rule, contradiction rule)"
else
  fail "guard findings:"
  printf '%s\n' "$guards" | sed 's/^/      /'
fi

# --- 4. docs parity -------------------------------------------------------------
# The translation must carry the same sections as the original: compare anchors,
# and refuse to compare emptiness with emptiness.

if [ ! -f docs/index.html ] || [ ! -f docs/index.ru.html ]; then
  fail "docs parity: a docs page is missing"
else
  en="$(grep -o 'id="[^"]*"' docs/index.html | sort -u)"
  ru="$(grep -o 'id="[^"]*"' docs/index.ru.html | sort -u)"
  n_en="$(printf '%s\n' "$en" | grep -c . || true)"
  if [ "${n_en:-0}" -lt 10 ]; then
    fail "docs parity: only ${n_en:-0} anchors in index.html — page truncated?"
  elif [ "$en" = "$ru" ]; then
    pass "docs parity ($n_en anchors in both)"
  else
    fail "docs anchors differ between index.html and index.ru.html:"
    diff <(printf '%s\n' "$en") <(printf '%s\n' "$ru") | sed 's/^/      /'
  fi
fi

# --- 5. behavior against an isolated HOME ---------------------------------------
# Windows python reads USERPROFILE, msys python reads HOME — set both, then assert
# the interpreter agrees before anything writes, otherwise the "isolated" run would
# land in the real data directory and prove nothing. Covers all eight wrappers and
# every documented card_integrity exit code, including the unparseable-json path.

FH="$(mktemp -d)" || { fail "mktemp failed — behavior checks skipped"; FH=""; }
if [ -n "$FH" ]; then
  FHW="$(cygpath -w "$FH" 2>/dev/null || printf '%s' "$FH")"
  iso() { HOME="$FH" USERPROFILE="$FHW" "$@"; }

  seen="$(iso "$PY" -c "import os;print(os.path.expanduser('~'))" 2>/dev/null || true)"
  case "$seen" in
    "$FH"|"$FHW")
      pass "isolated HOME honored ($seen)"

      printf '%s' '{"session_id":"rc1","cwd":"/tmp/Proj","tool_name":"Bash","tool_input":{"command":"npm test"}}' \
        | iso bash scripts/collect-friction.sh tool_failure >/dev/null 2>&1
      if grep -q '"event": "tool_failure"' "$FH"/.claude/agentwright/pending/*.jsonl 2>/dev/null; then
        pass "collect-friction journals a tool_failure event"
      else
        fail "collect-friction wrote no tool_failure event into the isolated HOME"
      fi
      printf '%s' '{"session_id":"rc2","cwd":"/tmp/Proj","tool_name":"Bash","tool_input":{"command":"python3 rc_private_cmd.py"},"error":"Exit code 127\nbash: rc_private_tool: command not found"}' \
        | iso bash scripts/collect-friction.sh tool_failure >/dev/null 2>&1
      rc2="$(cat "$FH"/.claude/agentwright/pending/*rc2*.jsonl 2>/dev/null)"
      if printf '%s' "$rc2" | grep -q '"category": "python"' \
         && printf '%s' "$rc2" | grep -q '"error_class": "cmd_not_found"' \
         && printf '%s' "$rc2" | grep -q '"exit_code": 127'; then
        pass "collect-friction derives category, error class and exit code"
      else
        fail "collect-friction did not derive python/cmd_not_found/127 from a failure payload"
      fi
      if printf '%s' "$rc2" | grep -q 'rc_private'; then
        fail "PRIVACY: command or error text reached the journal"
      else
        pass "command and error text stay out of the journal"
      fi
      if [ -s "$FH/.claude/agentwright/state/py" ]; then
        pass "interpreter cache created ($(head -1 "$FH/.claude/agentwright/state/py"))"
      else
        fail "interpreter cache was not created by the first wrapper run"
      fi

      out="$(iso bash scripts/scan-artifacts.sh "$FH" 2>/dev/null || true)"
      if printf '%s' "$out" | "$PY" -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if "scanned_at" in d and "error" not in d else 1)' 2>/dev/null; then
        pass "scan-artifacts emits facts json (scanned_at present, no error key)"
      else
        fail "scan-artifacts did not emit usable facts json"
      fi

      out="$(iso bash scripts/session-shapes.sh 2>/dev/null || true)"
      if printf '%s' "$out" | "$PY" -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if "sessions" in d and "error" not in d else 1)' 2>/dev/null; then
        pass "session-shapes emits shapes json (sessions present, no error key)"
      else
        fail "session-shapes did not emit usable shapes json"
      fi

      out="$(iso bash scripts/score-trajectory.sh 2>/dev/null || true)"
      if printf '%s' "$out" | "$PY" -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if "runs" in d else 1)' 2>/dev/null; then
        pass "score-trajectory emits trajectory json"
      else
        fail "score-trajectory did not emit trajectory json"
      fi

      out="$(iso bash scripts/product-metrics.sh --json 2>/dev/null || true)"
      if printf '%s' "$out" | "$PY" -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if "installed_collecting" in d else 1)' 2>/dev/null; then
        pass "product-metrics emits funnel json"
      else
        fail "product-metrics did not emit funnel json"
      fi

      if iso bash scripts/log-friction.sh "release-check probe note" >/dev/null 2>&1 \
         && grep -q '"event": "manual"' "$FH"/.claude/agentwright/pending/*-manual.jsonl 2>/dev/null; then
        pass "log-friction records a manual note (exit 0)"
      else
        fail "log-friction did not record a manual note"
      fi

      out="$(printf '%s' '{"model":{"display_name":"RCModel"}}' | iso bash scripts/statusline-example.sh 2>/dev/null || true)"
      case "$out" in
        *RCModel*) pass "statusline echoes the incoming model name" ;;
        *)         fail "statusline did not echo the incoming model name (got: '$out')" ;;
      esac

      iso bash scripts/card-integrity.sh check >/dev/null 2>&1; rc_empty=$?
      printf '{"score": 50}' > "$FH/.claude/agentwright/scorecard.json"
      iso bash scripts/card-integrity.sh stamp >/dev/null 2>&1; rc_stamp=$?
      iso bash scripts/card-integrity.sh check >/dev/null 2>&1; rc_sealed=$?
      iso "$PY" -c 'import json,os;p=os.path.expanduser("~/.claude/agentwright/scorecard.json");d=json.load(open(p));d["score"]=99;json.dump(d,open(p,"w"))' 2>/dev/null
      iso bash scripts/card-integrity.sh check >/dev/null 2>&1; rc_tamper=$?
      iso "$PY" -c 'import json,os;p=os.path.expanduser("~/.claude/agentwright/scorecard.json");d=json.load(open(p));d.pop("integrity",None);json.dump(d,open(p,"w"))' 2>/dev/null
      iso bash scripts/card-integrity.sh check >/dev/null 2>&1; rc_unseal=$?
      printf '{ broken' > "$FH/.claude/agentwright/scorecard.json"
      iso bash scripts/card-integrity.sh check >/dev/null 2>&1; rc_corrupt=$?
      if [ "$rc_empty" -eq 3 ] && [ "$rc_stamp" -eq 0 ] && [ "$rc_sealed" -eq 0 ] && [ "$rc_tamper" -eq 5 ] && [ "$rc_unseal" -eq 4 ] && [ "$rc_corrupt" -eq 5 ]; then
        pass "card-integrity exit contract holds (3/0/0/5/4/5 for empty/stamp/sealed/tampered/unsealed/corrupt)"
      else
        fail "card-integrity exit contract broken (got $rc_empty/$rc_stamp/$rc_sealed/$rc_tamper/$rc_unseal/$rc_corrupt, expected 3/0/0/5/4/5)"
      fi
      ;;
    *)
      fail "isolated HOME NOT honored (interpreter reports '$seen') — behavior checks skipped"
      ;;
  esac
fi

# --- summary --------------------------------------------------------------------

if [ "$FAILED" -eq 0 ]; then
  printf '\nrelease-check: all checks passed\n'
else
  printf '\nrelease-check: FAILURES above\n'
fi
exit "$FAILED"
