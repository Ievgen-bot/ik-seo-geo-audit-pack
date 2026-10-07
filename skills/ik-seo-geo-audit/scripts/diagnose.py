#!/usr/bin/env python3
"""diagnose.py — stage A of ik-seo-geo-audit: which skills are installed, are they up to date on GitHub,
which local tools exist. Read-only; stdlib only. Writes the result to
~/.config/ik-seo-geo-audit/state/last-diagnose.json and prints a Markdown report.

usage: diagnose.py [--size full|light] [--offline] [--pretend-missing a,b] [--json]

Version logic per installed third-party skill:
  * installed as a Claude Code plugin (installed_plugins.json has gitCommitSha): outdated when the
    latest upstream commit touching the skill path is NOT contained in the installed commit;
  * synced by the Claude app (~/.claude/plugins/synced): auto-updated by the app -> "managed";
  * a plain folder (~/.claude/skills, ~/.agents/skills): git-blob SHA of the local file vs the upstream
    file at HEAD; equal -> up to date, different -> "differs" (outdated or locally edited).
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
HERE = Path(__file__).resolve()
SKILL_DIR = HERE.parent.parent
PACK_ROOT = SKILL_DIR.parent.parent
CFG = HOME / ".config" / "ik-seo-geo-audit"
MANIFEST = json.load(open(SKILL_DIR / "manifest" / "skills.json", encoding="utf-8"))

# ---------- GitHub access (gh if present, else anonymous HTTPS) ----------
_cache = {}
def gh_api(path):
    if path in _cache:
        return _cache[path]
    data = None
    if shutil.which("gh"):
        try:
            out = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=30)
            if out.returncode == 0:
                data = json.loads(out.stdout)
        except Exception:
            data = None
    if data is None:
        try:
            req = urllib.request.Request("https://api.github.com/" + path,
                                         headers={"Accept": "application/vnd.github+json", "User-Agent": "ik-seo-geo-audit"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
        except Exception as e:
            data = {"_error": str(e)}
    _cache[path] = data
    return data

def latest_commit_for_path(repo, path):
    d = gh_api(f"repos/{repo}/commits?path={path}&per_page=1")
    if isinstance(d, list) and d:
        return d[0]["sha"], d[0]["commit"]["committer"]["date"]
    return None, None

def upstream_blob_sha(repo, path):
    d = gh_api(f"repos/{repo}/contents/{path}")
    return d.get("sha") if isinstance(d, dict) else None

def contains(repo, installed_sha, path_sha):
    """True when path_sha is an ancestor of (or equal to) installed_sha."""
    if installed_sha == path_sha:
        return True
    d = gh_api(f"repos/{repo}/compare/{path_sha}...{installed_sha}")
    if isinstance(d, dict) and "status" in d:
        return d["status"] in ("ahead", "identical")
    return None

def git_blob_sha(p):
    b = Path(p).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()

# ---------- where skills can be installed ----------
def installed_plugins():
    f = HOME / ".claude" / "plugins" / "installed_plugins.json"
    try:
        return json.load(open(f)).get("plugins", {})
    except Exception:
        return {}

def find_installs(entry):
    """Return a list of {path, how, plugin_sha?, plugin_version?}."""
    name, kind = entry["name"], entry["kind"]
    fname = "AGENT.md" if kind == "agent" else "SKILL.md"
    rel_tail = entry["path"]  # e.g. marketing/skills/seo-audit/SKILL.md
    hits = []
    # 1. Claude Code marketplace plugins
    for pid, recs in installed_plugins().items():
        plugin, _, market = pid.partition("@")
        if plugin != entry["plugin"]:
            continue
        for rec in recs:
            root = Path(rec.get("installPath", ""))
            for cand in [root / rel_tail, *root.glob(f"**/{name}/{fname}")]:
                if cand.exists():
                    hits.append({"path": str(cand), "how": f"plugin {pid}", "plugin_sha": rec.get("gitCommitSha"), "plugin_version": rec.get("version")})
                    break
    # 2. plugins synced by the Claude app (claude.ai catalog)
    synced = HOME / ".claude" / "plugins" / "synced"
    if synced.exists():
        for cand in synced.glob(f"*/{entry['plugin']}*/**/{name}/{fname}"):
            if "~g" in cand.as_posix() and not cand.as_posix().split(entry["plugin"])[1].startswith("~g"):
                continue
            hits.append({"path": str(cand), "how": "synced by Claude app"})
            break
        if kind == "agent":
            for cand in synced.glob(f"*/{entry['plugin']}*/agents/{name}/AGENT.md"):
                hits.append({"path": str(cand), "how": "synced by Claude app"}); break
    # 3. plain skill folders (only for names that are unique in the manifest)
    dup = sum(1 for e in MANIFEST["third_party"] if e["name"] == name) > 1
    if kind == "skill" and not dup:
        for root in [HOME / ".claude" / "skills", HOME / ".agents" / "skills"]:
            cand = root / name / "SKILL.md"
            if cand.exists():
                hits.append({"path": str(cand.resolve()), "how": f"folder {root}/{name}"})
                break
    # de-duplicate by resolved path
    seen, out = set(), []
    for h in hits:
        rp = os.path.realpath(h["path"])
        if rp not in seen:
            seen.add(rp); out.append(h)
    return out

def check_entry(entry, offline):
    installs = find_installs(entry)
    res = {"name": entry.get("id", entry["name"]), "kind": entry["kind"], "repo": entry["repo"], "plugin": entry["plugin"],
           "marketplace": entry["marketplace"], "size": entry["size"], "installs": installs}
    if not installs:
        res["status"] = "missing"; return res
    if offline:
        res["status"] = "installed (version not checked: offline)"; return res
    up_dir = entry["path"].rsplit("/", 1)[0] if "/" in entry["path"] else entry["path"]
    path_sha, path_date = latest_commit_for_path(entry["repo"], up_dir)
    res["upstream_last_commit"] = path_sha; res["upstream_last_commit_date"] = path_date
    best = installs[0]
    if best.get("plugin_sha") and path_sha:
        c = contains(entry["repo"], best["plugin_sha"], path_sha)
        res["status"] = "up to date" if c else ("outdated" if c is False else "unknown")
    elif best["how"].startswith("synced"):
        res["status"] = "managed (auto-updated by the Claude app)"
    else:
        up_blob = upstream_blob_sha(entry["repo"], entry["path"])
        local = git_blob_sha(best["path"])
        res["status"] = "up to date" if up_blob and up_blob == local else ("differs from upstream" if up_blob else "unknown")
    return res

def pack_version():
    local = (PACK_ROOT / "VERSION").read_text().strip() if (PACK_ROOT / "VERSION").exists() else None
    up = gh_api(f"repos/{MANIFEST['pack']['repo']}/contents/VERSION")
    remote = None
    if isinstance(up, dict) and up.get("content"):
        import base64
        remote = base64.b64decode(up["content"]).decode().strip()
    return {"local": local, "remote": remote, "root": str(PACK_ROOT),
            "status": ("up to date" if local and remote and local == remote else
                       "outdated" if local and remote and local != remote else
                       "not published yet" if remote is None else "unknown")}

def tools():
    t = {}
    t["python3"] = sys.version.split()[0]
    t["git"] = bool(shutil.which("git"))
    gh = shutil.which("gh")
    if gh:
        st = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        t["gh"] = "authenticated" if st.returncode == 0 else "installed, not logged in"
    else:
        t["gh"] = "missing (anonymous GitHub API: 60 requests/hour)"
    t["jev"] = bool(shutil.which("jev"))
    key = os.environ.get("TYPESAFE_API_KEY") or any(
        p.exists() and p.stat().st_size > 0 for p in [HOME / ".config/typesafe/api_key", HOME / ".config/typesafe/env"])
    t["typesafe_key"] = "present" if key else "missing"
    names = []
    for f in [HOME / ".claude.json", Path.cwd() / ".mcp.json"]:
        try:
            names += list(json.load(open(f)).get("mcpServers", {}).keys())
        except Exception:
            pass
    t["mcp_servers_configured"] = sorted(set(names))
    t["local_config"] = str(CFG / "local.md") if (CFG / "local.md").exists() else None
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="full", choices=["full", "light"])
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--pretend-missing", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    pretend = {x.strip() for x in a.pretend_missing.split(",") if x.strip()}
    results = []
    for e in MANIFEST["third_party"]:
        r = check_entry(e, a.offline)
        if r["name"] in pretend or e["name"] in pretend:
            r["installs"] = []; r["status"] = "missing"; r["pretended"] = True
        results.append(r)
    need = {"full": ("full", "light", "interview"), "light": ("light", "interview")}[a.size]
    required = [r for r in results if any(s in need for s in r["size"])]
    out = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "size": a.size,
        "pack": pack_version() if not a.offline else {"status": "not checked (offline)"},
        "tools": tools(),
        "skills": results,
        "to_install": sorted({(r["plugin"], r["marketplace"], r["repo"]) for r in required if r["status"] == "missing"}),
        "to_update": sorted({(r["plugin"], r["marketplace"], r["repo"]) for r in required
                             if r["status"] in ("outdated", "differs from upstream")}),
        "optional_missing": sorted({r["name"] for r in results if r["status"] == "missing" and r not in required}),
    }
    (CFG / "state").mkdir(parents=True, exist_ok=True)
    json.dump(out, open(CFG / "state" / "last-diagnose.json", "w"), indent=1, ensure_ascii=False)
    if a.json:
        print(json.dumps(out, indent=1, ensure_ascii=False)); return
    print(f"# Diagnostics ({out['checked_at']}, audit size: {a.size})\n")
    print(f"Pack: local {out['pack'].get('local')} · GitHub {out['pack'].get('remote')} · {out['pack']['status']}\n")
    print("| Skill | Plugin@marketplace | Status | Where |\n|---|---|---|---|")
    for r in results:
        where = r["installs"][0]["how"] if r["installs"] else "—"
        print(f"| {r['name']} ({r['kind']}) | {r['plugin']}@{r['marketplace']} | {r['status']} | {where} |")
    print("\n| Tool | State |\n|---|---|")
    for k, v in out["tools"].items():
        print(f"| {k} | {v} |")
    print(f"\nTo install (required for {a.size}): {[f'{p}@{m}' for p,m,_ in out['to_install']] or 'nothing'}")
    print(f"To update: {[f'{p}@{m}' for p,m,_ in out['to_update']] or 'nothing'}")
    print(f"Optional, not installed: {out['optional_missing'] or 'nothing'}")
    print(f"\nSaved: {CFG / 'state' / 'last-diagnose.json'}")

if __name__ == "__main__":
    main()
