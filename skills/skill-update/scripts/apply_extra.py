#!/usr/bin/env python3
"""apply_extra.py - second pass of the update: eligible copies inside OTHER git clones (e.g. ~/.notfair, ~/.ponytail:
the targets of the Hermes symlinks) that the main pass did not cover. Same safety model as apply_updates.py:
audited snapshot bytes only, file-level merge, per-target backup, own log (apply-log.run2.json), dry-run by default.

usage: apply_extra.py --su SU --run1 apply-log.run1.json [--apply] [--home DIR] [--backup-root DIR]"""
import argparse, datetime, glob, hashlib, json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_updates as AU  # noqa: E402
from tree_tool import tree_hash  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--su", required=True); ap.add_argument("--run1", required=True); ap.add_argument("--apply", action="store_true")
ap.add_argument("--home", default=str(Path.home())); ap.add_argument("--backup-root")
a = ap.parse_args()
su = Path(a.su).resolve(); AU.HOME = Path(a.home)
run1 = json.load(open(a.run1)); broot = Path(a.backup_root or run1["backup_root"])
man = {m["name"]: m for m in json.load(open(su / "manifest.json"))}
agent = {}
for f in sorted(glob.glob(str(su / "results/*.json"))):
    for r in json.load(open(f)):
        agent[r["skill"]] = r

plan, skipped = {}, []
from resultslib import load_results
layered = load_results(su)
for skill, e in run1["skills"].items():
    r, m = dict(agent[skill]), man[skill]
    r["snapshot"] = layered[skill].get("snapshot") or r.get("snapshot")
    done = {os.path.realpath(t["path"]) for t in e["targets"]}
    gc = m.get("git_clone") or {}
    clones = {o["path"]: o for o in gc.get("other_clones", [])}
    sn = r["snapshot"]; files = json.load(open(sn["files_json"]))["files"]
    for c in r.get("copies", []):
        rp = os.path.realpath(c["path"])
        if c.get("relation") != "dir-inside-other-clone" or c.get("state") not in ("identical_to_canonical", "stale_pristine") or rp in done or not os.path.isdir(rp):
            continue
        clone = next((cp for cp in clones if rp.startswith(cp + os.sep)), None)
        why = []
        if not clone:
            why.append("not inside a known other clone")
        else:
            dirty = subprocess.run(["git", "--no-optional-locks", "-C", clone, "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
            ours = set()
            for prev in (os.environ.get("PRIOR_LOGS", "").split(",") if os.environ.get("PRIOR_LOGS") else [str(x) for x in su.glob("apply-log-*.json")]):
                if prev and os.path.exists(prev):
                    pl = json.load(open(prev))
                    ours |= {os.path.realpath(os.path.join(t["path"], x)) for e2 in pl["skills"].values() for t in e2["targets"] for x in t["w"] + t["d"]}
            if any(os.path.realpath(os.path.join(clone, d[3:])) not in ours for d in dirty):
                why.append("clone has local changes not made by this run")
            if subprocess.run(["git", "-C", clone, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() != clones[clone]["local_head"]:
                why.append("clone HEAD moved since manifest")
        bk_old = broot / skill / "canonical"          # pre-update copy of the canonical (taken by the main pass)
        if bk_old.is_dir():
            d = AU.subprocess.run(["python3", str(su / "tools/tree_tool.py"), "diff", str(bk_old), rp, "--ignore-mode"], capture_output=True, text=True).stdout
            if not json.loads(d).get("identical"):
                why.append("copy differs from the pre-update canonical backup")
        else:
            why.append("no pre-update canonical backup to compare with")
        # the snapshot itself must still be intact
        actual = tree_hash(Path(sn["dir"]))["files"]
        if {k: v["sha256"] for k, v in actual.items()} != {k: v["sha256"] for k, v in files.items()}:
            why.append("snapshot changed since audit")
        if why:
            skipped.append((skill, rp, "; ".join(why))); continue
        plan.setdefault(skill, []).append((rp, sn, files))

log = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "dry_run": not a.apply, "backup_root": str(broot),
       "skills": {}, "clones": {}, "lock": None, "errors": [], "skipped": {s: w for s, _, w in skipped}, "run": "extra-copies"}
print(("APPLY" if a.apply else "DRY-RUN") + f": {sum(len(v) for v in plan.values())} extra targets in {len(plan)} skills; skipped {len(skipped)}")
for skill, items in plan.items():
    entry = {"mechanism": "merge-extra", "targets": [], "upstream_commit": items[0][1]["commit"]}
    for rp, sn, files in items:
        label = "other-clone-" + hashlib.sha1(rp.encode()).hexdigest()[:8]
        bk = broot / skill / label
        if a.apply:
            if not bk.exists():
                AU.backup_dir(Path(rp), bk)
        w, d = AU.merge(Path(sn["dir"]), files, Path(rp), sn.get("removed_upstream_files", []), not a.apply, log)
        entry["targets"].append({"label": label, "path": rp, "write": len(w), "delete": len(d), "w": w, "d": d, "backup": str(bk)})
        print(f"  {skill:24s} {rp.replace(a.home, '~'):58s} +{len(w)}/-{len(d)}")
    log["skills"][skill] = entry
for s, p, w in skipped:
    print(f"  SKIP {s} {p.replace(a.home, '~')}: {w}")
if a.apply:
    bad = 0
    for skill, items in plan.items():
        for rp, sn, files in items:
            for rel, meta in files.items():
                f = Path(rp) / rel
                if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != meta["sha256"]:
                    print("  VERIFY MISMATCH", skill, rel); bad += 1; break
    json.dump(log, open(su / os.environ.get("EXTRA_LOG", f"apply-log-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-extra.json"), "w"), ensure_ascii=False, indent=1)
    print("VERIFY OK: extra copies carry the audited bytes" if not bad else f"VERIFY FAILED: {bad}")
    sys.exit(1 if bad else 0)
