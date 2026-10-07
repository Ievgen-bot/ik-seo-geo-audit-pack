#!/usr/bin/env python3
"""apply_updates.py - apply VERIFIED skill snapshots produced by the audit agents (or roll the change back).

  apply_updates.py --su DIR                       dry-run plan (default, writes nothing)
  apply_updates.py --su DIR --apply               perform changes with backups + apply-log.json
  apply_updates.py --su DIR --verify LOG          re-check the current state against a log
  apply_updates.py --rollback LOG [--yes]         restore backups recorded in LOG (dry-run without --yes)
Options: --only a,b  --ff-clones (opt-in)  --hold-clones owner/repo,...  --backup-root DIR  --lock FILE  --home DIR

Safety model: only status UPDATE_READY with security SAFE; snapshot bytes are re-hashed against the audit's files.json;
the local canonical must be unchanged since the manifest was built; only upstream-owned files are written (local-only
files such as .venv are never touched); every target dir is backed up first; git clones are fast-forwarded to the exact
audited commit (never HEAD-at-apply-time) and non-updated skills of the same repo are pinned to their old content.
"""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

JUNK = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
HOME = Path.home()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tree_tool import tree_hash  # noqa: E402
from resultslib import load_results  # noqa: E402


def git(repo, *args, check=False):
    r = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args], capture_output=True, text=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def rel_ok(rel):
    p = Path(rel)
    return not p.is_absolute() and ".." not in p.parts and rel not in ("", ".")


def fm_name(p: Path):
    try:
        m = re.match(r"^---\s*\n(.*?)\n---", p.read_text(errors="ignore")[:4000], re.S)
        mm = re.search(r"^name\s*:\s*(.+)$", m.group(1), re.M) if m else None
        return mm.group(1).strip().strip("'\"") if mm else None
    except Exception:
        return None


def load(su: Path):
    man = {m["name"]: m for m in json.load(open(su / "manifest.json"))}
    return man, load_results(su)


def validate(skill, r, m):
    """Return (ok, reasons[]). Does not write anything."""
    why = []
    if r.get("status") != "UPDATE_READY":
        return False, [f"status {r.get('status')}"]
    if (r.get("security") or {}).get("verdict") != "SAFE" and not r.get("owner_accepted"):
        why.append(f"security verdict {(r.get('security') or {}).get('verdict')}")
    if not (r.get("local_state") or {}).get("pristine", False):
        why.append("local copy not pristine")
    sn = r.get("snapshot") or {}
    sd, fj = Path(sn.get("dir", "")), Path(sn.get("files_json", ""))
    if not sd.is_dir() or not fj.is_file():
        return False, why + ["snapshot dir/files_json missing"]
    declared = json.load(open(fj))["files"]
    actual = tree_hash(sd)["files"]
    if set(declared) != set(actual):
        why.append(f"snapshot file set differs from files.json (extra {sorted(set(actual) - set(declared))[:3]}, missing {sorted(set(declared) - set(actual))[:3]})")
    else:
        bad = [k for k in declared if declared[k]["sha256"] != actual[k]["sha256"]]
        if bad:
            why.append(f"snapshot content changed since audit: {bad[:3]}")
    if any(not rel_ok(k) for k in actual):
        why.append("unsafe relative path in snapshot")
    if any(v["mode"] == "symlink" for v in actual.values()):
        why.append("symlink inside snapshot")
    if sum(v["size"] for v in actual.values()) > 60_000_000:
        why.append("snapshot larger than 60 MB")
    if "SKILL.md" not in actual:
        why.append("snapshot has no SKILL.md")
    can = Path(m["canonical"])
    if not can.is_dir():
        why.append("canonical dir missing")
    else:
        tid = tree_hash(can)["tree_id"]
        if tid != m["canonical_tree_id"]:
            why.append(f"canonical changed since manifest (was {m['canonical_tree_id']}, now {tid})")
    return (not why), why


def backup_dir(src: Path, dst: Path):
    shutil.copytree(src, dst, symlinks=True, ignore=shutil.ignore_patterns(*JUNK, ".DS_Store", "._*"))


def merge(snap: Path, files, target: Path, removed, dry, log):
    """File-level merge of snapshot into target. Returns (written, deleted)."""
    written, deleted = [], []
    for rel, meta in sorted(files.items()):
        dst = target / rel
        src = snap / rel
        if dst.is_file() and not dst.is_symlink() and hashlib.sha256(dst.read_bytes()).hexdigest() == meta["sha256"]:
            want = int(meta["mode"], 8) & 0o111
            if (dst.stat().st_mode & 0o111) == want:
                continue
        written.append(rel)
        if dry:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".apply-tmp")
        tmp.write_bytes(src.read_bytes())
        os.chmod(tmp, int(meta["mode"], 8) & 0o777 or 0o644)
        os.replace(tmp, dst)
    for rel in sorted(removed or []):
        dst = target / rel
        if rel_ok(rel) and rel not in files and dst.is_file() and not dst.is_symlink():
            deleted.append(rel)
            if not dry:
                dst.unlink()
    if not dry:  # prune empty dirs left by deletions
        for rel in deleted:
            d = (target / rel).parent
            while d != target and d.is_dir() and not any(d.iterdir()):
                d.rmdir(); d = d.parent
    return written, deleted


def main():
    global HOME
    ap = argparse.ArgumentParser()
    ap.add_argument("--su"); ap.add_argument("--apply", action="store_true"); ap.add_argument("--verify")
    ap.add_argument("--rollback"); ap.add_argument("--yes", action="store_true")
    ap.add_argument("--release", default="", help="comma list: apply these skills even though the orchestrator held them (their agent verdict must have been SAFE)"); ap.add_argument("--only"); ap.add_argument("--ff-clones", action="store_true", help="OPT-IN: fast-forward git clones to the audited commit (default: file-level merge only)"); ap.add_argument("--hold-clones", default="")
    ap.add_argument("--backup-root", default=None)
    ap.add_argument("--lock", default=None)
    ap.add_argument("--home", default=str(Path.home()))
    a = ap.parse_args()
    HOME = Path(a.home)
    a.backup_root = a.backup_root or str(HOME / ".claude/skill-sources/_backups" / datetime.date.today().isoformat())
    a.lock = a.lock or str(HOME / ".agents/.skill-lock.json")
    if a.rollback:
        return rollback(Path(a.rollback), a.yes)
    su = Path(a.su).resolve()
    man, res = load(su)
    for rel in filter(None, a.release.split(",")):
        raw = load_results(su, decisions=False).get(rel)
        if raw and raw.get("status") == "UPDATE_READY":
            res[rel] = raw
            print(f"released from hold: {rel}")
        else:
            print(f"cannot release {rel}: agent status was {raw.get('status') if raw else 'unknown'}")
    if a.verify:
        return verify(su, json.load(open(a.verify)), man, res)
    only = set(filter(None, (a.only or "").split(",")))
    hold = set(filter(None, a.hold_clones.split(",")))
    dry = not a.apply
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    log = {"started": now, "dry_run": dry, "backup_root": a.backup_root, "skills": {}, "clones": {}, "lock": None, "skipped": {}, "errors": []}

    # ---- 1. validate ----
    ready = {}
    for skill, r in sorted(res.items()):
        if only and skill not in only:
            continue
        if r.get("status") != "UPDATE_READY":
            continue
        m = man.get(skill)
        if not m:
            log["skipped"][skill] = ["not in manifest"]; continue
        ok, why = validate(skill, r, m)
        (ready.__setitem__(skill, (r, m)) if ok else log["skipped"].__setitem__(skill, why))

    # ---- 2. group clone-managed skills ----
    by_clone = {}
    for skill, (r, m) in ready.items():
        gc = m.get("git_clone")
        if gc and a.ff_clones and gc["origin"] not in hold:
            by_clone.setdefault(gc["path"], []).append(skill)
    clone_plan = {}
    for cpath, skills in by_clone.items():
        gc = man[skills[0]]["git_clone"]
        commits = {ready[s][0]["snapshot"]["commit"] for s in skills}
        if len(commits) != 1:
            for s in skills:
                log["skipped"][s] = [f"snapshots of one repo come from different commits {sorted(c[:8] for c in commits)}"]
                ready.pop(s, None)
            continue
        U = commits.pop()
        clones = [cpath] + [o["path"] for o in gc.get("other_clones", [])]
        problems = []
        for c in clones:
            if git(c, "status", "--porcelain"):
                problems.append(f"{c} is dirty")
            if c == cpath and git(c, "rev-parse", "HEAD") != gc["local_head"]:
                problems.append(f"{c} HEAD moved since manifest")
        # pins: other skills of this repo that are NOT being updated but whose content would change at U -> keep old
        pins = []
        for sk, mm in man.items():
            g2 = mm.get("git_clone")
            if g2 and g2["path"] == cpath and sk not in ready:
                rr = res.get(sk, {})
                if rr.get("status") not in ("UP_TO_DATE",):
                    pins.append({"skill": sk, "relpath": g2["relpath"], "status": rr.get("status", "NOT_AUDITED")})
        clone_plan[cpath] = {"origin": gc["origin"], "commit": U, "clones": clones, "skills": skills, "pins": pins, "problems": problems,
                             "old_heads": {c: git(c, "rev-parse", "HEAD") for c in clones}}
        if problems:
            for s in skills:
                log["skipped"][s] = problems; ready.pop(s, None)
            clone_plan.pop(cpath)

    # ---- 3. per-skill plan ----
    for skill, (r, m) in ready.items():
        sn = r["snapshot"]; files = json.load(open(sn["files_json"]))["files"]
        in_clone = m["git_clone"] is not None and m["git_clone"]["path"] in clone_plan
        targets = []
        if not in_clone:
            targets.append(("canonical", m["canonical"]))
        ff_roots = [x for cp in clone_plan.values() for x in cp["clones"]]
        for c in r.get("copies", []):
            rp = os.path.realpath(c["path"])
            if any(rp.startswith(x + os.sep) for x in ff_roots):
                continue  # lives inside a clone that is fast-forwarded as a whole
            if c.get("state") in ("identical_to_canonical", "stale_pristine") and c.get("relation") in ("separate-copy", "dir-inside-other-clone", "nested-repo-copy"):
                targets.append(("copy-" + hashlib.sha1(rp.encode()).hexdigest()[:8], rp))
        entry = {"mechanism": "git-clone-ff" if in_clone else ("lock+merge" if m.get("lock") else "merge"), "targets": [], "upstream_commit": sn["commit"]}
        for label, path in targets:
            w, d = merge(Path(sn["dir"]), files, Path(path), sn.get("removed_upstream_files", []), True, log)
            entry["targets"].append({"label": label, "path": path, "write": len(w), "delete": len(d), "w": w, "d": d})
        log["skills"][skill] = entry
    log["clones"] = clone_plan

    # ---- 4. print plan ----
    print(f"{'DRY-RUN PLAN' if dry else 'APPLY'}: {len(ready)} skills ready, {len(log['skipped'])} skipped, {len(clone_plan)} clone groups")
    for skill, e in log["skills"].items():
        t = "; ".join(f"{x['label']} +{x['write']}/-{x['delete']}" for x in e["targets"]) or "(via clone fast-forward)"
        print(f"  {skill:34s} {e['mechanism']:13s} {t}")
    for cpath, cp in clone_plan.items():
        print(f"  CLONE {cp['origin']} -> {cp['commit'][:8]}  clones={[c.replace(str(HOME), '~') for c in cp['clones']]} skills={len(cp['skills'])} pins={[p['skill'] for p in cp['pins']]}")
    for skill, why in log["skipped"].items():
        print(f"  SKIP {skill}: {'; '.join(why)[:200]}")
    if dry:
        json.dump(log, open(su / "apply-plan.json", "w"), ensure_ascii=False, indent=1)
        print("dry-run only; plan saved to apply-plan.json"); return 0

    # ---- 5. APPLY ----
    broot = Path(a.backup_root); broot.mkdir(parents=True, exist_ok=True)
    lockp = Path(a.lock); shutil.copy2(lockp, broot / (lockp.name + ".bak"))
    log["lock_backup"] = str(broot / (lockp.name + ".bak"))
    counts_before = {rt: len(list((HOME / rt).iterdir())) for rt in (".claude/skills", ".agents/skills", ".codex/skills") if (HOME / rt).is_dir()}
    log["root_entry_counts_before"] = counts_before
    # 5a. clones
    for cpath, cp in clone_plan.items():
        try:
            for c in cp["clones"]:
                git(c, "fetch", "--no-tags", "origin", cp["commit"], check=True)
                git(c, "merge", "--ff-only", cp["commit"], check=True)
                assert git(c, "rev-parse", "HEAD") == cp["commit"], "HEAD != audited commit"
                for p in cp["pins"]:
                    git(c, "checkout", cp["old_heads"][c], "--", p["relpath"], check=True)
            cp["applied"] = True
        except Exception as e:
            cp["applied"] = False; log["errors"].append(f"clone {cpath}: {e}")
            for c in cp["clones"]:  # restore to the clean old state
                git(c, "reset", "--hard", cp["old_heads"][c])
            for s in cp["skills"]:
                log["skills"][s]["mechanism"] = "merge(fallback)"
                m = man[s]; log["skills"][s]["targets"].insert(0, {"label": "canonical", "path": m["canonical"], "write": 0, "delete": 0, "w": [], "d": []})
    # 5b. file-level merges with backup
    for skill, e in log["skills"].items():
        r, m = ready[skill]; sn = r["snapshot"]; files = json.load(open(sn["files_json"]))["files"]
        for t in e["targets"]:
            src = Path(t["path"])
            bk = broot / skill / t["label"]
            if not bk.exists():
                backup_dir(src, bk)
            t["backup"] = str(bk)
            w, d = merge(Path(sn["dir"]), files, src, sn.get("removed_upstream_files", []), False, log)
            t["w"], t["d"], t["write"], t["delete"] = w, d, len(w), len(d)
    # 5c. lock
    lock = json.load(open(lockp)); changed = []
    for skill, (r, m) in ready.items():
        if m.get("lock") and skill in lock["skills"] and (r["versions"].get("upstream_tree_sha") or r["versions"].get("latest_commit")):
            old_hash = lock["skills"][skill]["skillFolderHash"]
            # root-level skills store a COMMIT sha in the npx-skills lock, folder skills store the folder TREE sha
            is_commit_kind = old_hash == (r["versions"].get("installed_commit") or "") or (m["lock"]["skillPath"] == "SKILL.md")
            lock["skills"][skill]["skillFolderHash"] = (r["versions"].get("latest_commit") if is_commit_kind else None) or r["versions"].get("upstream_tree_sha") or r["versions"].get("latest_commit")
            lock["skills"][skill]["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            changed.append(skill)
    if changed:
        tmp = lockp.with_name(lockp.name + ".apply-tmp"); tmp.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n"); os.replace(tmp, lockp)
    log["lock"] = {"file": str(lockp), "updated": changed}
    log["root_entry_counts_after"] = {rt: len(list((HOME / rt).iterdir())) for rt in counts_before}
    lp = su / f"apply-log-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-updates.json"; json.dump(log, open(lp, "w"), ensure_ascii=False, indent=1)
    log["su"] = str(su)
    print(f"applied. log: {lp}")
    return verify(su, log, man, res)


def verify(su, log, man, res):
    """Check the CURRENT disk state against the audit snapshots and the pre-run manifest."""
    errs = []
    # 1) every updated skill carries exactly the audited bytes at every target
    for skill, e in log["skills"].items():
        r, m = res[skill], man[skill]
        files = json.load(open(r["snapshot"]["files_json"]))["files"]
        targets = [t["path"] for t in e["targets"]]
        if e["mechanism"] == "git-clone-ff":
            targets.append(m["canonical"])
        for tp in dict.fromkeys(targets):
            for rel, meta in files.items():
                f = Path(tp) / rel
                if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != meta["sha256"]:
                    errs.append(f"{skill}: {tp}/{rel} does not match the audited snapshot"); break
        nm = fm_name(Path(r["snapshot"]["dir"]) / "SKILL.md")
        if nm and fm_name(Path(m["canonical"]) / "SKILL.md") != nm:
            errs.append(f"{skill}: SKILL.md name mismatch after update")
    # 2) skills we did not update are byte-identical to the manifest
    updated = set(log["skills"])
    for skill, m in man.items():
        if skill in updated:
            continue
        can = Path(m["canonical"])
        if can.is_dir() and tree_hash(can)["tree_id"] != m["canonical_tree_id"]:
            errs.append(f"{skill}: NOT updated but its canonical changed (tree_id differs)")
    # 3) no new broken symlinks in the skill roots
    pre = {l["path"] for m in man.values() for l in m["locations"] if l.get("broken")}
    for rt in (".claude/skills", ".agents/skills", ".codex/skills"):
        root = HOME / rt
        for ent in (root.iterdir() if root.is_dir() else []):
            if ent.is_symlink() and not ent.exists() and str(ent) not in pre:
                started = datetime.datetime.fromisoformat(log["started"]).timestamp()
                if os.lstat(ent).st_mtime >= started - 1:   # only symlinks created/changed by this run count as new
                    errs.append(f"new broken symlink {ent}")
    # 4) entry counts per root unchanged
    b, af = log.get("root_entry_counts_before"), log.get("root_entry_counts_after")
    if b and af and b != af:
        errs.append(f"root entry counts changed: {b} -> {af}")
    # 5) lock file
    if log.get("lock") and log["lock"].get("updated"):
        lk = json.load(open(log["lock"]["file"]))["skills"]
        for sk in log["lock"]["updated"]:
            if lk[sk]["skillFolderHash"] not in (res[sk]["versions"].get("upstream_tree_sha"), res[sk]["versions"].get("latest_commit")):
                errs.append(f"lock hash for {sk} not updated")
    # 6) clones
    for cpath, cp in log.get("clones", {}).items():
        if not cp.get("applied"):
            continue
        for c in cp["clones"]:
            if git(c, "rev-parse", "HEAD") != cp["commit"]:
                errs.append(f"clone {c}: HEAD != audited commit")
            for pin in cp["pins"]:
                if subprocess.run(["git", "-C", c, "diff", "--quiet", cp["old_heads"][c], "--", pin["relpath"]]).returncode != 0:
                    errs.append(f"clone {c}: pinned {pin['skill']} differs from its old content")
    print("VERIFY OK: all checks passed" if not errs else f"VERIFY FAILED ({len(errs)}):")
    for x in errs[:30]:
        print("  -", x)
    return 1 if errs else 0


def rollback(logp: Path, yes: bool):
    log = json.load(open(logp))
    print(("ROLLBACK" if yes else "ROLLBACK DRY-RUN") + f" using {logp}")
    for skill, e in log["skills"].items():
        for t in e["targets"]:
            bk = Path(t.get("backup", "")); tgt = Path(t["path"])
            if not bk.is_dir():
                continue
            for rel in t["w"]:
                src = bk / rel
                print(f"  {skill}: {'restore' if src.exists() else 'remove new'} {rel}")
                if yes:
                    if src.exists():
                        tgt.joinpath(rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, tgt / rel)
                    elif (tgt / rel).exists():
                        (tgt / rel).unlink()
            for rel in t["d"]:
                src = bk / rel
                print(f"  {skill}: restore deleted {rel}")
                if yes and src.exists():
                    tgt.joinpath(rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, tgt / rel)
    for cpath, cp in log["clones"].items():
        if cp.get("applied"):
            for c, h in cp["old_heads"].items():
                print(f"  clone {c}: reset --hard {h[:8]}")
                if yes:
                    git(c, "reset", "--hard", h, check=True)
    if log.get("lock") and log["lock"].get("updated") and log.get("lock_backup"):
        print(f"  lock: restore {log['lock_backup']}")
        if yes:
            shutil.copy2(log["lock_backup"], log["lock"]["file"])
    print("done" if yes else "dry-run only; add --yes to execute")
    return 0


if __name__ == "__main__":
    sys.exit(main())
