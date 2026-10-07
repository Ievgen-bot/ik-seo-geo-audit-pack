#!/usr/bin/env python3
"""decide.py - orchestrator holds and owner decisions for a skill-update run.

  decide.py RUN show                                  list skills that are not plain UPDATE_READY/UP_TO_DATE
  decide.py RUN hold a,b --category "..." --reason "..."   orchestrator hold (agent said SAFE, other risk) + Ukrainian problem file
  decide.py RUN accept a,b [--force-unsafe]           OWNER said yes: release a hold, or build a snapshot for a REVIEW skill
                                                      from the exact tree the agent audited (byte-checked against upstream)
Writes RUN/decisions.json (holds) and RUN/owner.json (owner acceptances). Read-only on skill dirs."""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resultslib import load_results  # noqa: E402
from tree_tool import tree_hash  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("cmd", choices=["show", "hold", "accept"])
ap.add_argument("skills", nargs="?", default=""); ap.add_argument("--category", default="ПОТРІБНЕ РІШЕННЯ ВЛАСНИКА")
ap.add_argument("--reason", default=""); ap.add_argument("--force-unsafe", action="store_true")
a = ap.parse_args(); RUN = Path(a.run).resolve()
man = {m["name"]: m for m in json.load(open(RUN / "manifest.json"))}
raw = load_results(RUN, decisions=False)
dec_p, own_p = RUN / "decisions.json", RUN / "owner.json"
dec = json.load(open(dec_p)) if dec_p.exists() else {}
own = json.load(open(own_p)) if own_p.exists() else {}
names = [s for s in a.skills.split(",") if s]

if a.cmd == "show":
    cur = load_results(RUN)
    for k, r in sorted(cur.items()):
        if r["status"] not in ("UPDATE_READY", "UP_TO_DATE", "UPDATED"):
            why = (r.get("orchestrator_hold") or {}).get("reason") or (r.get("security") or {}).get("reasoning") or ""
            print(f"{r['status']:17s} {k:30s} {why[:150]}")
    sys.exit(0)

for k in names:
    r = raw.get(k)
    if not r:
        print(f"{k}: no result"); continue
    if a.cmd == "hold":
        if not a.reason:
            sys.exit("--reason is required")
        dec[k] = {"status": "FLAGGED_REVIEW", "orchestrator_hold": {"category": a.category, "reason": a.reason}, "_why": "orchestrator hold"}
        v = r.get("versions") or {}; u = r.get("upstream") or {}
        (RUN / "results/problems" / f"{k}.md").write_text("\n".join([
            f"# {k} — НЕ ОНОВЛЕНО: {a.category} (рішення оркестратора)",
            f"- Джерело: {u.get('repo')} ({u.get('path') or ''}), встановлено: {(v.get('installed_commit') or '?')[:8]}, остання: {(v.get('latest_commit') or '?')[:8]}",
            f"- Чому не оновлено: {a.reason}",
            "- Оцінка агента-аудитора: безпека SAFE; перевірений знімок збережено.",
            f"- Що можна зробити: залишити; або `decide.py RUN accept {k}` і застосувати.", ""]))
        print(f"held: {k}")
        continue
    # ---- accept (owner decision) ----
    dec.pop(k, None)
    if r["status"] == "UPDATE_READY":
        own[k] = {"status": "UPDATE_READY", "owner_accepted": True, "_why": "owner released the hold"}
        print(f"accepted (snapshot already audited): {k}"); continue
    if r["status"] == "FLAGGED_UNSAFE" and not a.force_unsafe:
        print(f"{k}: UNSAFE - refused without --force-unsafe"); continue
    if r["status"] not in ("FLAGGED_REVIEW", "FLAGGED_UNSAFE"):
        print(f"{k}: status {r['status']} cannot be accepted this way (DIVERGED -> merge3.py)"); continue
    if not (r.get("local_state") or {}).get("pristine", False):
        print(f"{k}: local copy has edits -> use merge3.py after accepting is not possible; merge by hand"); continue
    shard = man[k]["shard"]; audited = RUN / "work" / shard / "new" / k
    v = r["versions"]; U, old, path = v.get("latest_commit"), v.get("installed_commit"), (r.get("upstream") or {}).get("path") or ""
    clones = [d for d in (RUN / "work" / shard).iterdir() if (d / ".git").is_dir()]
    clone = next((d for d in clones if subprocess.run(["git", "-C", str(d), "cat-file", "-e", f"{U}^{{commit}}"]).returncode == 0), None)
    if not audited.is_dir() or not clone:
        print(f"{k}: audited tree or agent clone missing ({audited}) - rerun the shard"); continue
    tmp = RUN / "work" / "_accept" / k; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    subprocess.run(f'git -C "{clone}" archive {U} {path} | tar -x -C "{tmp}"', shell=True, check=True)
    snap = RUN / "snap" / k; shutil.rmtree(snap, ignore_errors=True); shutil.copytree(tmp / path if path else tmp, snap)
    d = json.loads(subprocess.run(["python3", str(RUN / "tools/tree_tool.py"), "diff", str(snap), str(audited)], capture_output=True, text=True).stdout)
    if not d["identical"]:
        print(f"{k}: upstream tree differs from what the agent audited - refused"); shutil.rmtree(snap); continue
    ls = lambda c: set(subprocess.run(["git", "-C", str(clone), "ls-tree", "-r", "--name-only", c, "--", path], capture_output=True, text=True).stdout.split())
    removed = sorted(p[len(path) + 1:] if path else p for p in (ls(old) - ls(U))) if old else []
    fj = RUN / "snap" / f"{k}.files.json"
    subprocess.run(["python3", str(RUN / "tools/tree_tool.py"), "hash", str(snap), "--out", str(fj)], capture_output=True)
    tree = subprocess.run(["git", "-C", str(clone), "rev-parse", f"{U}:{path}" if path else f"{U}^{{tree}}"], capture_output=True, text=True).stdout.strip()
    own[k] = {"status": "UPDATE_READY", "owner_accepted": True, "versions": {**v, "upstream_tree_sha": tree},
              "local_state": {**(r.get("local_state") or {}), "pristine": True},
              "snapshot": {"dir": str(snap), "files_json": str(fj), "commit": U, "removed_upstream_files": removed},
              "_why": f"owner accepted {r['status']}; snapshot = audited tree, byte-checked vs upstream"}
    print(f"accepted with new snapshot: {k} ({tree_hash(snap)['file_count']} files, removed upstream {len(removed)})")
json.dump(dec, open(dec_p, "w"), ensure_ascii=False, indent=1)
json.dump(own, open(own_p, "w"), ensure_ascii=False, indent=1)
