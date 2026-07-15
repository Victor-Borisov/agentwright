#!/usr/bin/env python3
"""Agentwright deterministic facts collector.

Scans ONLY user-authored configuration artifacts and the current repo.
Prints a single structured JSON object to stdout. The LLM layer interprets
these facts; it must never invent facts not present here.

Explicitly NEVER reads: ~/.claude/projects/ (transcripts),
~/.claude/usage-data/ (insights report, facets, session-meta),
or any conversation-derived data. (Anthropic Software Directory Policy §1.F)

Stdlib only. Exit code is always 0; problems are reported inside the JSON.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
CLAUDE_DIR = os.path.join(HOME, ".claude")
DATA_DIR = os.path.join(CLAUDE_DIR, "agentwright")

SECRET_VALUE_RE = re.compile(r"^(sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|xoxb-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})")
SECRET_FILE_RE = re.compile(
    r"AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|-----BEGIN( RSA)? PRIVATE KEY-----"
)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return {"__parse_error__": True}


def settings_facts(path):
    data = load_json(path)
    if data is None:
        return {"exists": False}
    if "__parse_error__" in data:
        return {"exists": True, "parse_error": True}
    perms = data.get("permissions", {}) or {}
    allow = perms.get("allow", []) or []
    mode = perms.get("defaultMode") or data.get("defaultMode")
    return {
        "exists": True,
        "deny_count": len(perms.get("deny", []) or []),
        "allow_count": len(allow),
        "allow_star": "*" in allow,
        "default_mode": mode,
        "bypass_permissions": mode == "bypassPermissions",
        "hooks_events": sorted((data.get("hooks", {}) or {}).keys()),
    }


def claude_md_facts(path):
    if not os.path.isfile(path):
        return {"exists": False}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return {"exists": True, "parse_error": True}
    return {
        "exists": True,
        "path": path,
        "lines": text.count("\n") + (1 if text and not text.endswith("\n") else 0),
        "bytes": len(text.encode("utf-8")),
        "imports": sum(1 for line in text.splitlines() if line.startswith("@")),
    }


def mcp_facts_from_servers(servers):
    servers = servers or {}
    suspect = False
    for server in servers.values():
        if not isinstance(server, dict):
            continue
        for value in (server.get("env", {}) or {}).values():
            if isinstance(value, str) and not value.startswith("$") and SECRET_VALUE_RE.match(value):
                suspect = True
    return {
        "exists": True,
        "servers": sorted(servers.keys()),
        "server_count": len(servers),
        "plaintext_secret_suspect": suspect,
    }


def mcp_facts(path):
    data = load_json(path)
    if data is None:
        return {"exists": False}
    if "__parse_error__" in data:
        return {"exists": True, "parse_error": True}
    return mcp_facts_from_servers(data.get("mcpServers", {}))


def user_mcp_facts():
    """User- and local-scope MCP servers live in ~/.claude.json (NOT ~/.claude/.mcp.json)."""
    data = load_json(os.path.join(HOME, ".claude.json"))
    if data is None:
        return {"exists": False}
    if "__parse_error__" in data:
        return {"exists": True, "parse_error": True}
    servers = dict(data.get("mcpServers", {}) or {})
    for proj in (data.get("projects", {}) or {}).values():
        if isinstance(proj, dict):
            servers.update(proj.get("mcpServers", {}) or {})
    return mcp_facts_from_servers(servers)


def installed_plugin_count():
    data = load_json(os.path.join(CLAUDE_DIR, "plugins", "installed_plugins.json"))
    if not data or "__parse_error__" in data:
        return 0
    total = 0
    for value in data.values():
        if isinstance(value, dict):
            total += len(value)
        elif isinstance(value, list):
            total += len(value)
    return total


def count(pattern):
    return len(glob.glob(pattern))


SCAN_SKIP_DIRS = (".git", "node_modules", ".venv", "venv", "dist", "build",
                  ".next", "target", "vendor", "__pycache__", ".cache")
SCAN_FILE_CAP = 5000


def secrets_scan(proj):
    if shutil.which("gitleaks"):
        try:
            with tempfile.NamedTemporaryFile(mode="r", suffix=".json", delete=False) as tmp:
                report_path = tmp.name
            subprocess.run(
                ["gitleaks", "detect", "--no-banner", "--exit-code", "0",
                 "--report-format", "json", "--report-path", report_path],
                cwd=proj, capture_output=True, text=True, timeout=120,
            )
            with open(report_path, encoding="utf-8") as f:
                findings = json.load(f)
            os.unlink(report_path)
            return {"tool": "gitleaks", "findings": len(findings), "truncated": False}
        except Exception:
            pass
    findings = 0
    scanned = 0
    truncated = False
    for root, dirs, files in os.walk(proj):
        dirs[:] = [d for d in dirs if d not in SCAN_SKIP_DIRS]
        for name in files:
            if scanned >= SCAN_FILE_CAP:
                truncated = True
                break
            path = os.path.join(root, name)
            try:
                if os.path.getsize(path) > 1_000_000:
                    continue
                scanned += 1
                with open(path, encoding="utf-8", errors="ignore") as f:
                    if SECRET_FILE_RE.search(f.read()):
                        findings += 1
            except Exception:
                continue
        if truncated:
            break
    return {"tool": "patterns", "findings": findings, "truncated": truncated}


def env_ignore_probe(path):
    """Ask git itself whether secret-shaped files would be ignored — this honors
    ALL ignore sources: the committed .gitignore, the repo-local (uncommitted)
    .git/info/exclude, and the user's global core.excludesFile. Returns
    {"effective": bool, "sources": [...]} or None when git is unavailable.
    `effective` keys on .env — the primary leak vector."""
    if not shutil.which("git"):
        return None
    try:
        out = subprocess.run(
            ["git", "check-ignore", "-v", "--", ".env", "probe.pem", "probe.key", "id_rsa"],
            cwd=path, capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    effective = False
    sources = set()
    for line in out.stdout.splitlines():
        if ":" not in line or "\t" not in line:
            continue
        src = line.split(":", 1)[0].strip()
        ignored = line.rsplit("\t", 1)[-1].strip()
        if src.endswith(".git/info/exclude") or src.endswith("info/exclude"):
            sources.add("local_exclude")
        elif src.endswith(".gitignore") and not os.path.isabs(src):
            sources.add("committed")
        else:
            sources.add("global")
        if ignored == ".env":
            effective = True
    return {"effective": effective, "sources": sorted(sources)}


def repo_facts(path):
    """Repo-scoped facts for one git repository (S2, B3, secrets probes)."""
    gitignore_env = False
    gi = os.path.join(path, ".gitignore")
    if os.path.isfile(gi):
        try:
            with open(gi, encoding="utf-8", errors="ignore") as f:
                gitignore_env = bool(re.search(r"(^|/)\.env|\*\.pem|\*\.key|id_rsa", f.read(), re.M))
        except Exception:
            pass
    ci_workflows = count(os.path.join(path, ".github", "workflows", "*.yml")) + \
        count(os.path.join(path, ".github", "workflows", "*.yaml"))
    precommit = any(os.path.exists(os.path.join(path, p)) for p in
                    (".pre-commit-config.yaml", ".husky/pre-commit", "lefthook.yml"))
    return {
        "is_git": True,
        "gitignore_env_covered": gitignore_env,
        "env_ignore": env_ignore_probe(path),
        "ci_workflows": ci_workflows,
        "gitlab_ci": os.path.isfile(os.path.join(path, ".gitlab-ci.yml")),
        "precommit": precommit,
        "secrets": secrets_scan(path),
    }


WORKSPACE_REPO_CAP = 20


def workspace_facts(root):
    """When cwd is not a repo, treat it as a workspace root: scan every immediate
    subdirectory that IS a git repo. Non-git subdirs are listed by name only and
    never scanned — personal folders legitimately hold un-ignored local files."""
    repos = []
    non_git = []
    truncated = False
    try:
        entries = sorted(os.listdir(root))
    except Exception:
        return None
    for name in entries:
        if name.startswith(".") or name in SCAN_SKIP_DIRS:
            continue
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if os.path.isdir(os.path.join(path, ".git")):
            if len(repos) >= WORKSPACE_REPO_CAP:
                truncated = True
                continue
            repos.append({
                "name": name,
                "path": path,
                **repo_facts(path),
                "claude_md": claude_md_facts(os.path.join(path, "CLAUDE.md")),
            })
        else:
            non_git.append(name)
    if not repos:
        return None
    return {"root": root, "repos": repos, "non_git_dirs": non_git,
            "truncated": truncated}


def main():
    proj = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())

    user = {
        "settings": settings_facts(os.path.join(CLAUDE_DIR, "settings.json")),
        "claude_md": claude_md_facts(os.path.join(CLAUDE_DIR, "CLAUDE.md")),
        "skills": len(glob.glob(os.path.join(CLAUDE_DIR, "skills", "**", "SKILL.md"), recursive=True)),
        "commands": len(glob.glob(os.path.join(CLAUDE_DIR, "commands", "**", "*.md"), recursive=True)),
        "agents": count(os.path.join(CLAUDE_DIR, "agents", "*.md")),
        "mcp": user_mcp_facts(),
        "memory_files": count(os.path.join(CLAUDE_DIR, "memory", "*.md")),
        "plugins": installed_plugin_count(),
    }

    project_level = {
        "settings": settings_facts(os.path.join(proj, ".claude", "settings.json")),
        "settings_local": settings_facts(os.path.join(proj, ".claude", "settings.local.json")),
        "claude_md": claude_md_facts(os.path.join(proj, "CLAUDE.md")),
        "skills": len(glob.glob(os.path.join(proj, ".claude", "skills", "**", "SKILL.md"), recursive=True)),
        "commands": len(glob.glob(os.path.join(proj, ".claude", "commands", "**", "*.md"), recursive=True)),
        "agents": count(os.path.join(proj, ".claude", "agents", "*.md")),
        "mcp": mcp_facts(os.path.join(proj, ".mcp.json")),
    }

    is_git = os.path.isdir(os.path.join(proj, ".git"))
    workspace = None
    if is_git:
        repo = repo_facts(proj)
    else:
        repo = {"is_git": False, "gitignore_env_covered": False, "ci_workflows": 0,
                "gitlab_ci": False, "precommit": False,
                "secrets": {"tool": "none", "findings": 0}}
        workspace = workspace_facts(proj)

    CAP_MAP = {"EnterPlanMode": "plan_mode", "ExitPlanMode": "plan_mode",
               "EnterWorktree": "worktree", "ExitWorktree": "worktree",
               "Task": "subagent", "Agent": "subagent", "mcp": "mcp",
               "WebSearch": "web", "WebFetch": "web", "LSP": "lsp"}
    pending_files = sorted(glob.glob(os.path.join(DATA_DIR, "pending", "*.jsonl")))
    events_by_type = {}
    categories = {}          # tool_failure categories (unchanged meaning)
    success_categories = {}  # tool_success categories (failure-ratio denominator)
    capabilities = set()     # levers the journal shows in active use
    effort_levels = {}
    pmode_levels = {}
    for path in pending_files:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    ev = str(entry.get("event", "unknown"))
                    events_by_type[ev] = events_by_type.get(ev, 0) + 1
                    cat = str(entry["category"]) if entry.get("category") else ""
                    if ev == "tool_failure" and cat:
                        categories[cat] = categories.get(cat, 0) + 1
                    elif ev == "tool_success" and cat:
                        success_categories[cat] = success_categories.get(cat, 0) + 1
                    elif ev == "tool_use":
                        lab = CAP_MAP.get(str(entry.get("tool", "")))
                        if lab:
                            capabilities.add(lab)
                    elif ev == "session_start":
                        if entry.get("effort"):
                            lv = str(entry["effort"])
                            effort_levels[lv] = effort_levels.get(lv, 0) + 1
                        if entry.get("pmode"):
                            pm = str(entry["pmode"])
                            pmode_levels[pm] = pmode_levels.get(pm, 0) + 1
        except Exception:
            continue
    pending_events = sum(events_by_type.values())

    previous = None
    card = load_json(os.path.join(DATA_DIR, "scorecard.json"))
    if card and "__parse_error__" not in card:
        previous = {
            "score": card.get("score"),
            "date": card.get("date"),
            "checklist_version": card.get("checklist_version"),
            "open_actions": sum(1 for a in card.get("actions", []) if a.get("verified") is None),
        }

    calibration = {"knowledge_version": None, "calibrated_for_claude_code": None,
                   "last_seen_claude_code": None, "stale": False}
    cal = load_json(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "references", "calibration.json"))
    if cal and "__parse_error__" not in cal:
        calibration["knowledge_version"] = cal.get("knowledge_version")
        calibration["calibrated_for_claude_code"] = cal.get("calibrated_for_claude_code")
    try:
        with open(os.path.join(DATA_DIR, "state", "cc-version"), encoding="utf-8") as f:
            calibration["last_seen_claude_code"] = f.read().strip()
    except Exception:
        pass
    try:
        seen = [int(x) for x in str(calibration["last_seen_claude_code"]).split(".")[:2]]
        cal_v = [int(x) for x in str(calibration["calibrated_for_claude_code"]).split(".")[:2]]
        calibration["stale"] = (seen[0] * 1000 + seen[1]) > (cal_v[0] * 1000 + cal_v[1])
    except Exception:
        pass

    print(json.dumps({
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": proj,
        "user": user,
        "project_level": project_level,
        "repo": repo,
        "workspace": workspace,
        "friction_journal": {
            "pending_events": pending_events,
            "pending_files": len(pending_files),
            "events_by_type": events_by_type,
            "failure_categories": categories,
            "success_categories": success_categories,
            "capabilities_used": sorted(capabilities),
            "effort_levels": effort_levels,
            "pmode_levels": pmode_levels,
        },
        "previous": previous,
        "calibration": calibration,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never crash the skill flow
        print(json.dumps({"error": str(exc)}))
    sys.exit(0)
