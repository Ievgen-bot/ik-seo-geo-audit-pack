#!/usr/bin/env python3
"""post_process.py - orchestrator post-processing between the audit and the apply (read-only on skill dirs).

1. verify nothing changed on disk since the manifest was built, then refresh manifest canonical_tree_id with tree_tool semantics
2. re-evaluate every local copy of every UPDATE_READY skill: identical_to_canonical | stale_pristine | diverged
   (stale_pristine = equals an OLDER upstream version byte-for-byte, checked against the agent's own blobless clone)
3. status fixes: DIVERGED although upstream did not change  ->  UP_TO_DATE (local edits only)
Writes overlay.json (+ manifest.json refresh) only with --write.   usage: post_process.py SU [--write]"""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

HOME = Path.home()
SU = Path(sys.argv[1]).resolve(); WRITE = "--write" in sys.argv
sys.path.insert(0, str(SU / "tools"))
from tree_tool import tree_hash  # noqa: E402
from resultslib import load_results  # noqa: E402

JUNK = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


def builder_tree_id(d: Path):  # exact replica of build_manifest.tree_id (kept to detect real changes since the manifest build)
    h = hashlib.sha256(); n = 0
    for p, dirs, files in os.walk(d):
        dirs[:] = sorted(x for x in dirs if x not in JUNK)
        for f in sorted(files):
            if f == ".DS_Store" or f.startswith("._") or f.endswith(".pyc"):
                continue
            fp = Path(p) / f
            try:
                h.update(str(fp.relative_to(d)).encode()); h.update(hashlib.sha256(fp.read_bytes()).digest()); n += 1
            except Exception:
                pass
        if n > 6000:
            break
    return h.hexdigest()[:16]


def diff_identical(a: Path, b: Path):
    r = subprocess.run(["python3", str(SU / "tools/tree_tool.py"), "diff", str(a), str(b), "--ignore-mode"], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"identical": False, "changed": [], "only_in_A": [], "only_in_B": []}


def agent_clone(shard, repo):
    base = SU / "work" / shard
    cands = [d for d in (base.iterdir() if base.is_dir() else []) if (d / ".git").is_dir()]
    urls = {d: subprocess.run(["git", "-C", str(d), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip().lower().rstrip("/").removesuffix(".git") for d in cands}
    exact = [d for d, u in urls.items() if u.endswith("/" + repo.lower())]
    if exact:
        return exact[0]
    owner = repo.lower().split("/")[0]
    same_owner = [d for d, u in urls.items() if "/" + owner + "/" in u]
    return same_owner[0] if len(same_owner) == 1 else (cands[0] if len(cands) == 1 else None)


man = {m["name"]: m for m in json.load(open(SU / "manifest.json"))}
res = load_results(SU)
changed = []
for k, m in man.items():
    can = Path(m["canonical"])
    if can.is_dir() and tree_hash(can)["tree_id"] != m["canonical_tree_id"]:
        changed.append(k)
print(f"[1] canonical changed on disk since manifest build: {changed or 'none'}")
new_ids = {k: tree_hash(Path(m["canonical"]))["tree_id"] for k, m in man.items() if Path(m["canonical"]).is_dir()}

overlay, stats = {}, {}
for k, r in sorted(res.items()):
    m = man.get(k)
    if not m:
        continue
    v = r.get("versions") or {}
    if r.get("status") == "DIVERGED" and v.get("installed_commit") and v.get("installed_commit") == v.get("latest_commit"):
        overlay.setdefault(k, {}).update({"status": "UP_TO_DATE", "_why": "DIVERGED but upstream did not change: local edits only (UP_TO_DATE per protocol 6.1)"})
    if r.get("status") != "UPDATE_READY":
        continue
    can = Path(m["canonical"]); u = r.get("upstream") or {}; sh = m["shard"]
    clone = agent_clone(sh, u.get("repo") or m["upstream"]["repo"])
    path = u.get("path") or m["upstream"].get("path") or ""
    locs = [dict(l) for l in m["locations"]]
    if k in {n for n, mm in man.items() if mm["upstream"]["repo"] == "coreyhaines31/marketingskills"}:
        nested = HOME / ".codex/skills/marketingskills/skills" / k
        if nested.is_dir():
            locs.append({"root": "codex", "path": str(nested), "kind": "dir", "realpath": str(nested.resolve()), "relation": "nested-repo-copy"})
    copies = []
    for l in locs:
        rp = Path(l["realpath"]); rel = l["relation"]
        e = {"path": l["path"], "relation": rel, "note": ""}
        if rel in ("is-canonical", "symlink-to-canonical", "symlink-into-other-clone", "symlink-elsewhere"):
            e["state"] = "symlink" if l["kind"] == "symlink" else "canonical"
        elif l.get("broken") or rel == "broken-symlink":
            e["state"] = "broken-symlink"
        elif rel in ("separate-copy", "dir-inside-other-clone", "nested-repo-copy") and rp.is_dir() and rp != can:
            d = diff_identical(rp, can)
            if d.get("identical"):
                e["state"] = "identical_to_canonical"
            else:
                st = "diverged"
                if clone and path:
                    b = subprocess.run(["python3", str(SU / "tools/find_baseline.py"), "--repo", str(clone), "--path", path, "--local", str(rp)], capture_output=True, text=True)
                    try:
                        j = json.loads(b.stdout)
                        if j.get("exact_commit"):
                            st = "stale_pristine"; e["note"] = f"equals upstream at {j['exact_commit']['commit'][:8]} ({j['exact_commit']['date'][:10]})"
                        else:
                            e["note"] = f"local edits: closest {((j.get('closest') or {}).get('commit') or '?')[:8]} jaccard {(j.get('closest') or {}).get('jaccard')}; differing {len((j.get('closest') or {}).get('differing', []))} files"
                    except Exception:
                        e["note"] = "baseline check failed"
                e["state"] = st
        else:
            e["state"] = "n/a"
        stats[e["state"]] = stats.get(e["state"], 0) + 1
        copies.append(e)
    overlay.setdefault(k, {}).update({"copies": copies, "_why": overlay.get(k, {}).get("_why", "copies reclassified by post_process")})

print("[2] copy states over UPDATE_READY skills:", stats)
bad = [(k, c["path"].replace(str(HOME), "~"), c["note"]) for k, o in overlay.items() for c in o.get("copies", []) if c["state"] == "diverged"]
print(f"    diverged real copies (will NOT be touched): {len(bad)}")
for x in bad[:20]:
    print("     -", *x)
print("[3] status fixes:", {k: o["status"] for k, o in overlay.items() if "status" in o} or "none")
if WRITE:
    shutil.copy2(SU / "manifest.json", SU / "manifest.pre-refresh.json")
    for m in json.load(open(SU / "manifest.json")):
        pass
    mm = json.load(open(SU / "manifest.json"))
    for m in mm:
        if m["name"] in new_ids:
            m["canonical_tree_id"] = new_ids[m["name"]]
    json.dump(mm, open(SU / "manifest.json", "w"), ensure_ascii=False, indent=1)
    json.dump(overlay, open(SU / "overlay.json", "w"), ensure_ascii=False, indent=1)
    print("written: manifest.json (ids refreshed), overlay.json")
else:
    print("(dry: nothing written; use --write)")
