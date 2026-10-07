#!/usr/bin/env python3
"""finalize.py - close a skill-update run: applied.json from the apply logs, registry.json refresh,
PROBLEMS.md + RESULTS.tsv, rollback.sh; optionally copy the report to a project folder.
usage: finalize.py RUN [--out PROJECT_OUTPUT_DIR] [--no-registry]"""
import argparse, datetime, json, os, shutil, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resultslib import load_results  # noqa: E402

def registry_path():
    """User data lives outside the skill so updates never overwrite it:
    $SKILL_UPDATE_REGISTRY, else ~/.config/skill-update/registry.json (created empty on first use)."""
    import os, json as _j
    from pathlib import Path as _P
    env = os.environ.get("SKILL_UPDATE_REGISTRY")
    p = _P(env).expanduser() if env else _P.home() / ".config" / "skill-update" / "registry.json"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_j.dumps({"version": 1, "updated": None, "skills": {}, "excluded": {}}, indent=1), encoding="utf-8")
    return p


ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--no-registry", action="store_true")
a = ap.parse_args(); RUN = Path(a.run).resolve(); SKILL = Path(__file__).resolve().parent.parent
logs = sorted(RUN.glob("apply-log-*.json"))
applied = {}
for lp in logs:
    l = json.load(open(lp))
    for k, e in l["skills"].items():
        x = applied.setdefault(k, {"status": "UPDATED", "applied_at": l["started"], "applied_targets": [], "logs": [], "_why": "applied"})
        x["applied_targets"] += [t["path"] for t in e["targets"]]; x["logs"].append(lp.name)
        if e.get("mechanism") == "owner-merge":
            x["merged_with_owner_edits"] = True
json.dump(applied, open(RUN / "applied.json", "w"), ensure_ascii=False, indent=1)
res = load_results(RUN)
(RUN / "rollback.sh").write_text("#!/bin/bash\n# Restore pre-update files from the backups recorded in the apply logs (newest first). DRY-RUN unless --yes.\nset -euo pipefail\nD=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
                                 + "".join(f'python3 "$D/tools/apply_updates.py" --rollback "$D/{lp.name}" "$@"\n' for lp in sorted(logs, key=lambda p: json.load(open(p))["started"], reverse=True)))
os.chmod(RUN / "rollback.sh", 0o755)
os.system(f'python3 "{RUN}/tools/build_report.py" "{RUN}" "{RUN}" >/dev/null')
if not a.no_registry:
    rp = registry_path(); reg = json.load(open(rp)); shutil.copy2(rp, RUN / "registry.before.json")
    today = datetime.date.today().isoformat()
    for k, r in res.items():
        u = r.get("upstream") or {}; v = r.get("versions") or {}; st = r["status"]
        if st == "NO_UPSTREAM":
            reg["skills"].pop(k, None); reg["excluded"][k] = f"no upstream found (own skill) — {today}"; continue
        e = reg["skills"].setdefault(k, {})
        if u.get("identity_verified"):
            e["repo"] = u.get("full_name_now") or u.get("repo") or e.get("repo"); e["path"] = u.get("path", e.get("path")); e["confidence"] = "verified"
        e.update({"last_status": st, "last_checked": today, "last_commit": v.get("latest_commit") if st in ("UPDATED", "UP_TO_DATE") else v.get("installed_commit")})
        e.pop("last_hold_reason", None)
        if st in ("FLAGGED_REVIEW", "FLAGGED_UNSAFE"):
            e["last_hold_reason"] = ((r.get("orchestrator_hold") or {}).get("reason") or (r.get("security") or {}).get("reasoning") or "")[:300]
        if st == "REMOVED_UPSTREAM":
            e["removed_upstream"] = True
        if st == "DIVERGED" or (applied.get(k) or {}).get("merged_with_owner_edits"):
            e["owner_edits"] = True
    reg["updated"] = today
    json.dump(reg, open(rp, "w"), ensure_ascii=False, indent=1)
if a.out:
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for f in ["PROBLEMS.md", "RESULTS.tsv", "applied.json", "decisions.json", "owner.json", "rollback.sh"] + [lp.name for lp in logs]:
        if (RUN / f).exists():
            shutil.copy2(RUN / f, out / f)
    shutil.copytree(RUN / "results", out / "results", dirs_exist_ok=True, ignore=shutil.ignore_patterns("files"))
    shutil.copytree(RUN / "tools", out / "tools", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
from collections import Counter


print("statuses:", dict(Counter(r["status"] for r in res.values())), "| logs:", len(logs), "| report:", RUN / "PROBLEMS.md", "| copied to:", a.out or "-")
