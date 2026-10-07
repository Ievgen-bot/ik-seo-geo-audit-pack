#!/usr/bin/env python3
"""Synthetic end-to-end test of apply_updates.py in a fake HOME (never touches real skills)."""
import json, os, shutil, subprocess, sys, hashlib
from pathlib import Path

SU = Path(sys.argv[1]).resolve()
T = SU / "work" / "_applytest"
shutil.rmtree(T, ignore_errors=True)
H = T / "home"
for r in (".claude/skills", ".agents/skills", ".codex/skills", ".claude/skill-sources"):
    (H / r).mkdir(parents=True)
TOOLS = SU / "tools"
TS = T / "su"; (TS / "results").mkdir(parents=True); (TS / "snap").mkdir()


def w(p, txt, mode=None):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt)
    if mode: os.chmod(p, mode)


def sh(*a, cwd=None, check=True):
    r = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode: raise SystemExit(f"FAILED {a}: {r.stderr}{r.stdout}")
    return r.stdout.strip()


def tid(d): return json.loads(sh("python3", str(TOOLS / "tree_tool.py"), "hash", str(d)))["tree_id"]


def snap(name, files, removed=(), commit="c2", tree_sha="newtreesha"):
    d = TS / "snap" / name
    for rel, txt in files.items(): w(d / rel, txt)
    fj = TS / "snap" / f"{name}.files.json"
    sh("python3", str(TOOLS / "tree_tool.py"), "hash", str(d), "--out", str(fj))
    return {"dir": str(d), "files_json": str(fj), "commit": commit, "file_count": len(files), "removed_upstream_files": list(removed)}, tree_sha


manifest, results = [], []
# ---- A: plain copy with local-only .venv + notes, removed upstream file, codex real copy ----
A = H / ".claude/skill-sources/mk/skills/aa"
w(A / "SKILL.md", "---\nname: aa\n---\nv1\n"); w(A / "scripts/x.sh", "echo old\n", 0o755); w(A / "refs/old.md", "same\n")
w(A / ".venv/lib/site.py", "local venv\n"); w(A / "notes-local.txt", "my local notes\n")
os.symlink(A, H / ".claude/skills/aa"); shutil.copytree(A, H / ".codex/skills/aa")
sn, ts = snap("aa", {"SKILL.md": "---\nname: aa\n---\nv2\n", "refs/old.md": "same\n", "refs/new.md": "added\n"}, removed=["scripts/x.sh"])
manifest.append({"name": "aa", "canonical": str(A), "canonical_tree_id": tid(A), "locations": [], "lock": None, "git_clone": None})
results.append({"skill": "aa", "status": "UPDATE_READY", "security": {"verdict": "SAFE"}, "local_state": {"pristine": True},
                "versions": {"upstream_tree_sha": ts}, "snapshot": sn,
                "copies": [{"path": str(H / ".codex/skills/aa"), "relation": "separate-copy", "state": "identical_to_canonical"}]})
# ---- B: lock-managed ----
B = H / ".agents/skills/bb"
w(B / "SKILL.md", "---\nname: bb\n---\nv1\n"); w(B / "extra.md", "e\n"); os.symlink(B, H / ".claude/skills/bb")
lock = {"version": 3, "skills": {"bb": {"source": "o/r", "sourceType": "github", "skillPath": "SKILL.md", "skillFolderHash": "oldhash", "installedAt": "2026-01-01T00:00:00.000Z", "updatedAt": "2026-01-01T00:00:00.000Z"}}, "dismissed": {}}
(H / ".agents/.skill-lock.json").write_text(json.dumps(lock, indent=2) + "\n")
sn, ts = snap("bb", {"SKILL.md": "---\nname: bb\n---\nv2\n", "extra.md": "e\n"}, tree_sha="newtreesha-bb")
manifest.append({"name": "bb", "canonical": str(B), "canonical_tree_id": tid(B), "locations": [], "lock": lock["skills"]["bb"], "git_clone": None})
results.append({"skill": "bb", "status": "UPDATE_READY", "security": {"verdict": "SAFE"}, "local_state": {"pristine": True},
                "versions": {"upstream_tree_sha": ts, "latest_commit": "commitbb", "installed_commit": "oldhash"}, "snapshot": sn, "copies": []})
# ---- C: git clone with 3 skills: cc updated, dd flagged (pin), ee up-to-date ----
bare, work = T / "upstream.git", T / "up-work"
sh("git", "init", "-q", "--bare", str(bare)); sh("git", "init", "-q", str(work))
sh("git", "-C", str(work), "config", "user.email", "t@t"); sh("git", "-C", str(work), "config", "user.name", "t")
for s in ("cc", "dd", "ee"): w(work / f"skills/{s}/SKILL.md", f"---\nname: {s}\n---\nv1\n")
sh("git", "-C", str(work), "add", "-A"); sh("git", "-C", str(work), "commit", "-qm", "c1")
sh("git", "-C", str(work), "branch", "-M", "main"); sh("git", "-C", str(work), "remote", "add", "origin", str(bare)); sh("git", "-C", str(work), "push", "-q", "origin", "main")
clone = H / ".claude/skill-sources/up"; sh("git", "clone", "-q", str(bare), str(clone))
c1 = sh("git", "-C", str(clone), "rev-parse", "HEAD")
w(work / "skills/cc/SKILL.md", "---\nname: cc\n---\nv2\n"); w(work / "skills/cc/new.md", "n\n"); w(work / "skills/dd/SKILL.md", "---\nname: dd\n---\nv2-suspicious\n")
sh("git", "-C", str(work), "add", "-A"); sh("git", "-C", str(work), "commit", "-qm", "c2"); sh("git", "-C", str(work), "push", "-q", "origin", "main")
c2 = sh("git", "-C", str(work), "rev-parse", "HEAD")
for s in ("cc", "dd", "ee"):
    os.symlink(clone / f"skills/{s}", H / f".claude/skills/{s}")
    manifest.append({"name": s, "canonical": str(clone / f"skills/{s}"), "canonical_tree_id": tid(clone / f"skills/{s}"), "locations": [], "lock": None,
                     "git_clone": {"path": str(clone), "origin": "test/up", "relpath": f"skills/{s}", "local_head": c1, "dirty_files": 0, "other_clones": []}})
sn, ts = snap("cc", {"SKILL.md": "---\nname: cc\n---\nv2\n", "new.md": "n\n"}, commit=c2, tree_sha="treecc")
results.append({"skill": "cc", "status": "UPDATE_READY", "security": {"verdict": "SAFE"}, "local_state": {"pristine": True}, "versions": {"upstream_tree_sha": ts}, "snapshot": sn, "copies": []})
results.append({"skill": "dd", "status": "FLAGGED_REVIEW", "security": {"verdict": "REVIEW"}})
results.append({"skill": "ee", "status": "UP_TO_DATE"})
json.dump(manifest, open(TS / "manifest.json", "w")); json.dump(results, open(TS / "results" / "t.json", "w"))

before = {k: tid(p) for k, p in {"aa": A, "bb": B, "dd": clone / "skills/dd", "ee": clone / "skills/ee"}.items()}
APPLY = ["python3", str(TOOLS / "apply_updates.py"), "--su", str(TS), "--home", str(H), "--backup-root", str(T / "backup"), "--ff-clones"]
print("=== DRY RUN"); print(sh(*APPLY))
assert tid(A) == before["aa"], "dry-run modified aa!"
print("=== APPLY"); out = sh(*APPLY, "--apply"); print(out)
assert "VERIFY OK" in out, "verify failed"
rd = lambda p: Path(p).read_text()
assert "v2" in rd(A / "SKILL.md") and (A / "refs/new.md").exists() and not (A / "scripts/x.sh").exists(), "A not merged"
assert (A / ".venv/lib/site.py").exists() and rd(A / "notes-local.txt") == "my local notes\n", "A local-only files lost!"
assert "v2" in rd(H / ".codex/skills/aa/SKILL.md") and not (H / ".codex/skills/aa/scripts/x.sh").exists(), "A codex copy not updated"
assert "v2" in rd(B / "SKILL.md") and json.load(open(H / ".agents/.skill-lock.json"))["skills"]["bb"]["skillFolderHash"] == "commitbb", "B/lock (root-level skill stores commit sha)"
assert sh("git", "-C", str(clone), "rev-parse", "HEAD") == c2, "clone not at c2"
assert "v2" in rd(clone / "skills/cc/SKILL.md") and "v1" in rd(clone / "skills/dd/SKILL.md"), "cc updated / dd pinned"
assert tid(clone / "skills/ee") == before["ee"], "ee changed"
print("=== ROLLBACK (dry)"); print(sh("python3", str(TOOLS / "apply_updates.py"), "--rollback", str(TS / "apply-log.json")))
print("=== ROLLBACK (yes)"); print(sh("python3", str(TOOLS / "apply_updates.py"), "--rollback", str(TS / "apply-log.json"), "--yes"))
assert tid(A) == before["aa"] and tid(B) == before["bb"], "A/B not restored"
assert sh("git", "-C", str(clone), "rev-parse", "HEAD") == c1 and tid(clone / "skills/dd") == before["dd"], "clone not restored"
assert json.load(open(H / ".agents/.skill-lock.json"))["skills"]["bb"]["skillFolderHash"] == "oldhash", "lock not restored"
assert (A / ".venv/lib/site.py").exists(), "venv lost on rollback"
print("ALL SELFTEST ASSERTIONS PASSED")

# ---- phase 2: default mode (no --ff-clones): file-level merge only, clone HEAD untouched ----
APPLY2 = [a for a in APPLY if a != "--ff-clones"]
print("=== PHASE 2: merge-only apply"); out = sh(*APPLY2, "--apply"); print(out)
assert "VERIFY OK" in out, "phase2 verify failed"
assert sh("git", "-C", str(clone), "rev-parse", "HEAD") == c1, "phase2 moved clone HEAD"
assert "v2" in rd(clone / "skills/cc/SKILL.md") and (clone / "skills/cc/new.md").exists(), "phase2 cc not merged"
assert "v1" in rd(clone / "skills/dd/SKILL.md") and tid(clone / "skills/ee") == before["ee"], "phase2 dd/ee touched"
print(sh("python3", str(TOOLS / "apply_updates.py"), "--rollback", str(TS / "apply-log.json"), "--yes"))
assert "v1" in rd(clone / "skills/cc/SKILL.md") and not (clone / "skills/cc/new.md").exists(), "phase2 rollback failed"
assert tid(A) == before["aa"] and tid(B) == before["bb"], "phase2 rollback A/B"
print("PHASE 2 PASSED")
