#!/usr/bin/env python3
"""apply_merges.py - apply 3-way merged trees (new upstream + owner's local edits) to explicit targets.
Each target must still match the tree_id recorded at planning time; every target is backed up first;
the log has the same shape as apply_updates.py logs, so `apply_updates.py --rollback LOG` restores it.

usage: apply_merges.py SPEC.json [--apply] [--log OUT.json] [--backup-root DIR]   (dry-run by default)"""
import argparse, datetime, hashlib, json, os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_updates as AU  # noqa: E402
from tree_tool import tree_hash, walk  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("spec"); ap.add_argument("--apply", action="store_true"); ap.add_argument("--log", default="apply-log.merges.json")
ap.add_argument("--backup-root", default=str(Path.home() / ".claude/skill-sources/_backups" / datetime.date.today().isoformat()))
a = ap.parse_args()
spec = json.load(open(a.spec)); broot = Path(a.backup_root)
log = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "dry_run": not a.apply,
       "backup_root": str(broot), "skills": {}, "clones": {}, "lock": None, "errors": [], "run": "owner-merges"}
bad = 0
for s in spec:
    tgt, mer = Path(s["target"]), Path(s["merged"])
    if tree_hash(tgt)["tree_id"] != s["pre_tree"]:
        print(f"  SKIP {s['skill']} {tgt}: changed since planning"); bad += 1; continue
    files = {rel: {"sha256": hashlib.sha256(fp.read_bytes()).hexdigest(), "mode": "755" if os.access(fp, os.X_OK) else "644"} for rel, fp in walk(mer)}
    remove = sorted(set(r for r, _ in walk(tgt)) - set(files))
    label = "merge-" + hashlib.sha1(str(tgt.resolve()).encode()).hexdigest()[:8]
    bk = broot / s["skill"] / label
    if a.apply and not bk.exists():
        AU.backup_dir(tgt, bk)
    w, d = AU.merge(mer, files, tgt, remove, not a.apply, log)
    log["skills"].setdefault(s["skill"], {"mechanism": "owner-merge", "targets": [], "upstream_commit": s.get("upstream_commit")})["targets"].append(
        {"label": label, "path": str(tgt), "write": len(w), "delete": len(d), "w": w, "d": d, "backup": str(bk)})
    print(f"  {s['skill']:22s} {s['kind']:15s} {str(tgt).replace(str(Path.home()), '~'):55s} +{len(w)}/-{len(d)}")
    if a.apply:
        for rel, meta in files.items():
            f = tgt / rel
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != meta["sha256"]:
                print("    VERIFY MISMATCH", rel); bad += 1; break
        if any((tgt / r).exists() for r in remove):
            print("    VERIFY: removed file still present"); bad += 1
if a.apply:
    json.dump(log, open(a.log, "w"), ensure_ascii=False, indent=1)
    print("VERIFY OK: merged trees applied" if not bad else f"VERIFY FAILED/SKIPPED: {bad}")
else:
    print("dry-run only")
sys.exit(1 if bad else 0)
