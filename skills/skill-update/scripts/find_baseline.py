#!/usr/bin/env python3
"""Find which upstream commit a local skill directory corresponds to (the 'installed version').

Uses git metadata only: a blobless clone is enough (`git ls-tree` needs trees, not blobs).

usage: find_baseline.py --repo CLONE_DIR --path UPSTREAM_PATH --local LOCAL_DIR [--lock-hash TREE_SHA] [--max 400] [--until ISO_DATE]

Output JSON:
  exact_commit      newest commit whose upstream folder equals the local folder (same file set, same content) or None
  lock_commit       commit whose tree sha for the path equals --lock-hash (npx-skills lock), or None
  subset_commits    newest commits where every local file equals upstream (upstream may have extra files)
  closest           best partial match by Jaccard overlap {commit, date, jaccard, only_local, only_upstream, differing}
  checked           number of commits examined
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tree_tool import walk, gitblob  # noqa: E402

JUNK = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


def git(repo, *args):
    return subprocess.run(["git", "-c", "core.quotePath=false", "-C", repo, *args], capture_output=True, text=True).stdout


def junk(rel):
    parts = rel.split("/")
    return any(p in JUNK for p in parts) or parts[-1] == ".DS_Store" or parts[-1].startswith("._") or parts[-1].endswith(".pyc")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True); ap.add_argument("--path", default="")
    ap.add_argument("--local", required=True); ap.add_argument("--lock-hash")
    ap.add_argument("--max", type=int, default=400); ap.add_argument("--until")
    a = ap.parse_args()
    P = a.path.strip("/")
    local = {}
    for rel, fp in walk(Path(a.local)):
        try:
            local[rel] = gitblob(fp.read_bytes())
        except OSError:
            continue  # dangling symlink or unreadable file
    cmd = ["log", f"--max-count={a.max}", "--format=%H%x09%cI"]
    if a.until:
        cmd.append(f"--until={a.until}")
    cmd += ["--", P] if P else []
    commits = [l.split("\t") for l in git(a.repo, *cmd).splitlines() if l.strip()]
    head = git(a.repo, "rev-parse", "HEAD").strip()
    if head and not commits:
        commits.insert(0, [head, git(a.repo, "log", "-1", "--format=%cI", head).strip() or "HEAD"])
    res = {"exact_commit": None, "lock_commit": None, "subset_commits": [], "closest": None, "checked": 0, "local_files": len(local)}
    best = (-1.0, None)
    for h, date in commits:
        res["checked"] += 1
        if a.lock_hash:
            ref = f"{h}:{P}" if P else f"{h}^{{tree}}"
            if git(a.repo, "rev-parse", ref).strip() == a.lock_hash:
                res["lock_commit"] = {"commit": h, "date": date, "kind": "tree"}
            elif h == a.lock_hash:
                res["lock_commit"] = {"commit": h, "date": date, "kind": "commit"}
        out = git(a.repo, "ls-tree", "-r", "-z", h, "--", P) if P else git(a.repo, "ls-tree", "-r", "-z", h)
        up = {}
        for line in out.split("\0"):
            if not line:
                continue
            meta, _, name = line.partition("\t")
            _mode, typ, sha = meta.split()
            rel = name[len(P) + 1:] if P and name.startswith(P + "/") else name
            if typ == "blob" and not junk(rel):
                up[rel] = sha
        common = set(local) & set(up)
        same = {r for r in common if local[r] == up[r]}
        only_local, only_up = sorted(set(local) - set(up)), sorted(set(up) - set(local))
        differing = sorted(common - same)
        union = len(set(local) | set(up)) or 1
        j = len(same) / union
        if not only_local and not differing:
            if not only_up and res["exact_commit"] is None:
                res["exact_commit"] = {"commit": h, "date": date}
            if len(res["subset_commits"]) < 5:
                res["subset_commits"].append({"commit": h, "date": date, "extra_upstream_files": len(only_up)})
        if j > best[0]:
            best = (j, {"commit": h, "date": date, "jaccard": round(j, 3), "only_local": only_local[:25], "only_upstream": only_up[:25], "differing": differing[:25]})
        if res["exact_commit"] and (res["lock_commit"] or not a.lock_hash):
            break
    res["closest"] = best[1]
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
