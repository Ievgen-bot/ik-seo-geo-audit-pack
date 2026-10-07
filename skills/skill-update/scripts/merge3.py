#!/usr/bin/env python3
"""merge3.py - keep the owner's local edits while taking the new upstream "engine" (3-way merge per file).

  merge3.py RUN [--skills a,b]

Builds RUN/merges/<label>/ trees + RUN/merges/spec.json (input of apply_merges.py) for:
  A) DIVERGED skills (canonical has owner edits, upstream newer): base = the upstream version the owner edited
     (found by blob hashes + smallest line diff over the path history in the agent's clone), local = canonical,
     new = upstream at the audited commit. Copies equal to the canonical or to an older pristine upstream get the
     same merged tree.
  B) diverged COPIES of UPDATE_READY skills (e.g. ~/.claude copy with a 'Media storage' note): base = canonical
     (pre-update), local = copy, new = the audited snapshot.
Rules per file: untouched locally -> upstream (incl. deletion); changed only locally -> yours; both -> git merge-file.
Files with conflicts are reported and the whole skill is left OUT of spec.json. Read-only on skill dirs.
Always read the printed "merged vs NEW upstream" diff: it must contain only the owner's lines."""
import argparse, difflib, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

RUN = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tree_tool import walk, tree_hash, gitblob  # noqa: E402
from resultslib import load_results  # noqa: E402

H = Path.home()


def git(clone, *args, text=True):
    r = subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(clone), *args], capture_output=True, text=text)
    return r.stdout


def agent_clone(shard, repo):
    base = RUN / "work" / shard
    cands = [d for d in (base.iterdir() if base.is_dir() else []) if (d / ".git").is_dir()]
    urls = {d: git(d, "remote", "get-url", "origin").strip().lower().rstrip("/").removesuffix(".git") for d in cands}
    exact = [d for d, u in urls.items() if u.endswith("/" + repo.lower())]
    if exact:
        return exact[0]
    owner = repo.lower().split("/")[0]
    same_owner = [d for d, u in urls.items() if "/" + owner + "/" in u]
    return same_owner[0] if len(same_owner) == 1 else (cands[0] if len(cands) == 1 else None)


def tree_at(clone, commit, path):
    out = git(clone, "ls-tree", "-r", "-z", commit, "--", path) if path else git(clone, "ls-tree", "-r", "-z", commit)
    m = {}
    for line in out.split("\0"):
        if line:
            meta, _, name = line.partition("\t")
            _mode, typ, sha = meta.split()
            if typ == "blob":
                m[name[len(path) + 1:] if path else name] = sha
    return m


def blob(clone, sha):
    return subprocess.run(["git", "-C", str(clone), "cat-file", "-p", sha], capture_output=True).stdout


def find_base(clone, path, local, U):
    lb = {r: gitblob(fp.read_bytes()) for r, fp in walk(local)}
    commits = git(clone, "log", "--format=%H", "--max-count=200", U, "--", path).split() if path else git(clone, "log", "--format=%H", "--max-count=200", U).split()
    scored = []
    for c in commits:
        t = tree_at(clone, c, path)
        same = sum(1 for r, s in t.items() if lb.get(r) == s)
        scored.append((same, c, t))
    if not scored:
        return None, {}
    top = max(s for s, _, _ in scored)
    best = None
    for same, c, t in [x for x in scored if x[0] == top][:40]:
        cost = 0
        for r, s in t.items():
            if r in lb and lb[r] != s:
                old = blob(clone, s).decode(errors="ignore").splitlines(); new = (local / r).read_text(errors="ignore").splitlines()
                for l in difflib.ndiff(old, new):
                    cost += 10 if l.startswith("- ") else (1 if l.startswith("+ ") else 0)
        cost += 50 * (len(set(t) - set(lb)) + len(set(lb) - set(t)))
        if best is None or cost < best[0]:
            best = (cost, c, t)
    return best[1], best[2]


def materialize(clone, t, dst):
    shutil.rmtree(dst, ignore_errors=True); dst.mkdir(parents=True)
    for r, s in t.items():
        p = dst / r; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(blob(clone, s))
    return dst


def three_way(base, local, new, out):
    B, L, N = ({r: fp for r, fp in walk(Path(d))} if d and Path(d).is_dir() else {} for d in (base, local, new))
    shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True); conflicts = []
    for rel in sorted(set(B) | set(L) | set(N)):
        b, l, n = B.get(rel), L.get(rel), N.get(rel)
        rb, rl, rn = (x.read_bytes() if x else None for x in (b, l, n))
        if rl == rb:
            res = rn
        elif rn == rb:
            res = rl
        elif None in (rb, rl, rn):
            conflicts.append(rel); res = rl
        else:
            tmp = out.parent / (out.name + ".tmp"); tmp.write_bytes(rl)
            r = subprocess.run(["git", "merge-file", "-p", str(tmp), str(b), str(n)], capture_output=True); tmp.unlink()
            if r.returncode != 0:
                conflicts.append(rel)
            res = r.stdout
        if res is None:
            continue
        p = out / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(res)
        src = n or l
        if src and os.access(src, os.X_OK):
            os.chmod(p, 0o755)
    return conflicts


def show(new, merged):
    d = subprocess.run(["diff", "-ru", str(new), str(merged)], capture_output=True, text=True).stdout
    lines = [l for l in d.splitlines() if (l[:1] in "+-" and not l.startswith(("+++", "---"))) or l.startswith("Only in")]
    return "\n".join("     " + l[:170] for l in lines[:14]) or "     (identical to new upstream)"


def main():
    global RUN
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("--skills")
    a = ap.parse_args(); RUN = Path(a.run).resolve()
    only = set(filter(None, (a.skills or "").split(",")))
    man = {m["name"]: m for m in json.load(open(RUN / "manifest.json"))}
    res = load_results(RUN)
    M = RUN / "merges"; M.mkdir(exist_ok=True)
    spec, report = [], []
    for k, r in sorted(res.items()):
        if only and k not in only:
            continue
        m = man.get(k)
        if not m:
            continue
        if r.get("status") == "DIVERGED":   # ---- case A
            u = r.get("upstream") or {}; v = r.get("versions") or {}; U = v.get("latest_commit"); path = u.get("path") or ""
            clone = agent_clone(m["shard"], u.get("repo") or m["upstream"]["repo"])
            if not clone or not U:
                report.append(f"{k}: no agent clone/commit -> merge by hand"); continue
            local = Path(m["canonical"])
            bc, bt = find_base(clone, path, local, U)
            if not bc:
                report.append(f"{k}: base not found"); continue
            base = materialize(clone, bt, M / f"_base-{k}")
            new = materialize(clone, tree_at(clone, U, path), M / f"_new-{k}")
            out = M / k; c = three_way(base, local, new, out)
            print(f"=== {k} [canonical] base {bc[:8]} -> new {U[:8]} conflicts={c}\n   merged vs NEW upstream (must be only YOUR lines):\n{show(new, out)}")
            if c:
                report.append(f"{k}: conflicts {c} -> not merged"); continue
            spec.append({"skill": k, "kind": "canonical", "target": str(local), "merged": str(out), "upstream_commit": U})
            for l in m["locations"]:
                rp = os.path.realpath(l["path"])
                if l.get("relation") not in ("separate-copy", "dir-inside-other-clone") or l.get("broken") or rp == str(local):
                    continue
                if tree_hash(Path(rp))["tree_id"] == tree_hash(local)["tree_id"] or any(
                        tree_at(clone, cc, path) == {x: gitblob(fp.read_bytes()) for x, fp in walk(Path(rp))}
                        for cc in git(clone, "log", "--format=%H", "--max-count=200", U, "--", path).split()):
                    spec.append({"skill": k, "kind": "copy", "target": rp, "merged": str(out), "upstream_commit": U})
                else:
                    report.append(f"{k}: copy {rp} has its own edits -> left alone")
        elif r.get("status") == "UPDATE_READY" and r.get("snapshot"):   # ---- case B
            for c in r.get("copies", []):
                if c.get("state") != "diverged" or c.get("relation") not in ("separate-copy", "dir-inside-other-clone"):
                    continue
                rp = os.path.realpath(c["path"])
                if "/.hermes/" in rp:
                    report.append(f"{k}: Hermes-own copy {rp} left alone"); continue
                lab = f"{k}@{hashlib.sha1(rp.encode()).hexdigest()[:6]}"; out = M / lab
                cc = three_way(m["canonical"], rp, r["snapshot"]["dir"], out)
                print(f"=== {k} [copy {rp.replace(str(H), '~')}] conflicts={cc}\n   merged vs NEW upstream:\n{show(r['snapshot']['dir'], out)}")
                if cc:
                    report.append(f"{lab}: conflicts {cc} -> not merged"); continue
                spec.append({"skill": k, "kind": "copy-with-owner-edits", "target": rp, "merged": str(out), "upstream_commit": r["snapshot"].get("commit")})
    for s in spec:
        s["pre_tree"] = tree_hash(Path(s["target"]))["tree_id"]
    json.dump(spec, open(M / "spec.json", "w"), indent=1)
    print(f"\nspec: {M / 'spec.json'} ({len(spec)} targets)")
    for x in report:
        print("  NOTE", x)


if __name__ == "__main__":
    main()
