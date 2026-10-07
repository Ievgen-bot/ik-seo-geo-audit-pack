#!/usr/bin/env python3
"""plan_run.py - choose WHICH skills to update and prepare a run directory for the audit agents (read-only on skills).

  plan_run.py --list                                   show registry grouped by repo/family + unregistered candidates
  plan_run.py --topic "hyperframes video" [--dry]      select by words (name, repo, family, SKILL.md description)
  plan_run.py --skills humanizer,grilling [--dry]      select exact skills (family members are added unless --no-family)
  plan_run.py --repo obra/superpowers [--dry]          select every skill of a repo
  plan_run.py --all [--dry]                            everything in the registry (except removed_upstream)
Options: --include-unregistered  --include-removed  --no-family  --max-per-shard 8  --run-dir DIR  --no-pin

Without --dry it writes: RUN/{manifest.json,cards/,prompts/,tools/,PROTOCOL.md,results/problems/,snap/,work/}.
"""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys
from collections import defaultdict
from pathlib import Path

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




SKILL_DIR = Path(__file__).resolve().parent.parent
H = Path.home()
ROOTS = [("claude", H / ".claude/skills"), ("agents", H / ".agents/skills"), ("codex", H / ".codex/skills"), ("hermes", H / ".hermes/skills")]
JUNK = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def frontmatter(md: Path):
    try:
        head = md.read_text(errors="ignore")[:6000]
    except Exception:
        return {}
    m = re.match(r"^---\s*\n(.*?)\n---", head, re.S)
    if not m:
        return {}
    out = {}
    for key in ("name", "description"):
        mm = re.search(rf"^{key}\s*:\s*(.*)$", m.group(1), re.M)
        if mm:
            val = mm.group(1).strip()
            if val in (">", "|", ">-", "|-", ""):  # block scalar: take the indented lines below
                rest = m.group(1)[mm.end():].splitlines()
                val = " ".join(l.strip() for l in rest[1:] if l.startswith((" ", "\t")))[:600] if rest else ""
            out[key] = val.strip("'\"")
    return out


def tree_id(d: Path):  # same formula as tools/tree_tool.py (unreadable/dangling entries skipped)
    h = hashlib.sha256(); n = 0
    for p, dirs, files in os.walk(d):
        dirs[:] = sorted(x for x in dirs if x not in JUNK)
        for f in sorted(files):
            if f == ".DS_Store" or f.startswith("._") or f.endswith(".pyc"):
                continue
            fp = Path(p) / f
            try:
                data = fp.read_bytes(); fp.lstat()
            except OSError:
                continue
            h.update(str(fp.relative_to(d)).encode()); h.update(hashlib.sha256(data).digest()); n += 1
    return h.hexdigest()[:16], n


# ---------- local locations ----------
def mk_loc(rname, d: Path):
    real = d.resolve()
    return {"root": rname, "path": str(d), "kind": "symlink" if d.is_symlink() else "dir", "realpath": str(real),
            "broken": not real.exists(), "entry_name": d.name, "fm_name": frontmatter(real / "SKILL.md").get("name") if real.exists() else None}


def scan_locations():
    all_locs = []
    for rname, root in ROOTS:
        if not root.is_dir():
            continue
        if rname == "hermes":
            stack = [(root, 0)]
            while stack:
                base, depth = stack.pop()
                try:
                    entries = sorted(os.scandir(base), key=lambda e: e.name)
                except OSError:
                    continue
                for e in entries:
                    if e.name.startswith(".") or e.name in JUNK:
                        continue
                    d = Path(e.path)
                    if not (e.is_dir(follow_symlinks=True) or d.is_symlink()):
                        continue
                    if (d / "SKILL.md").is_file() or (d.is_symlink() and not d.resolve().exists()):
                        all_locs.append(mk_loc(rname, d))
                    elif depth < 2 and not d.is_symlink():
                        stack.append((d, depth + 1))
            continue
        for e in sorted(root.iterdir()):
            if e.name.startswith(".") or not (e.is_dir() or e.is_symlink()):
                continue
            if (e / "SKILL.md").is_file() or (e.is_symlink() and not e.resolve().exists()):
                all_locs.append(mk_loc(rname, e))
    by = defaultdict(list)
    for l in all_locs:
        for key in {l["entry_name"], l["fm_name"]} - {None}:
            if l not in by[key]:
                by[key].append(l)
    return by


def find_clones(repos):
    clones = {}
    cands = [p for p in H.glob(".[!.]*") if (p / ".git").exists()] + [p for p in (H / ".claude/skill-sources").glob("*") if (p / ".git").exists()]
    cands += [H / ".codex/superpowers"]
    for c in cands:
        m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", sh(["git", "-C", str(c), "remote", "get-url", "origin"]) or "")
        if m:
            name = m.group(1)
            for r in repos:  # renamed repos (notfair -> notfair-plugin) still match on owner + prefix
                if name.lower() == r.lower() or (name.split("/")[0].lower() == r.split("/")[0].lower() and r.split("/")[1].lower().startswith(name.split("/")[1].lower())):
                    clones[str(c)] = r
    return clones


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true"); g.add_argument("--all", action="store_true")
    g.add_argument("--skills"); g.add_argument("--topic"); g.add_argument("--repo")
    ap.add_argument("--include-unregistered", action="store_true"); ap.add_argument("--include-removed", action="store_true")
    ap.add_argument("--no-family", action="store_true"); ap.add_argument("--max-per-shard", type=int, default=8)
    ap.add_argument("--run-dir"); ap.add_argument("--dry", action="store_true"); ap.add_argument("--no-pin", action="store_true")
    a = ap.parse_args()

    reg = json.load(open(registry_path()))
    R, EXC = reg["skills"], reg["excluded"]
    locs = scan_locations()
    present = {k for k in R if locs.get(k)}
    unreg = sorted(k for k in locs if k not in R and k not in EXC and not k.startswith("ik-") and not k.startswith("ckm:")
                   and any(l["root"] != "hermes" for l in locs[k]) and not all(l["broken"] for l in locs[k])
                   and not all(l["fm_name"] in R for l in locs[k]))

    def desc(k):
        for l in locs.get(k, []):
            if not l["broken"]:
                return frontmatter(Path(l["realpath"]) / "SKILL.md").get("description", "")
        return ""

    if a.list:
        by = defaultdict(list)
        for k in sorted(present):
            by[R[k]["repo"]].append(k + ("*" if R[k].get("owner_edits") else "") + ("(removed)" if R[k].get("removed_upstream") else ""))
        print(f"Registry: {len(present)} skills installed locally, {len(by)} repos (* = your local edits, merged on update)")
        for repo, ks in sorted(by.items(), key=lambda x: -len(x[1])):
            fam = sorted({R[k.rstrip('*').split('(')[0]].get("family") for k in ks} - {None})
            print(f"  {repo:42s} {len(ks):3d}  {'family:' + ','.join(fam) + '  ' if fam else ''}{', '.join(ks[:8])}{' …' if len(ks) > 8 else ''}")
        print(f"Unregistered local skills (provenance unknown, not ik-*): {len(unreg)}: {', '.join(unreg[:30])}")
        return 0

    sel = set()
    if a.all:
        sel = set(present)
    elif a.skills:
        want = [s.strip() for s in a.skills.split(",") if s.strip()]
        missing = [s for s in want if s not in locs]
        if missing:
            print("not installed locally:", missing)
        sel = {s for s in want if s in locs}
    elif a.repo:
        sel = {k for k in present if R[k]["repo"].lower() == a.repo.lower()}
    elif a.topic:
        toks = [t for t in re.findall(r"[\w-]{3,}", a.topic.lower())]
        scored = []
        for k in sorted(present | (set(unreg) if a.include_unregistered else set())):
            e = R.get(k, {})
            strong = sum(1 for t in toks if t in k.lower() or t in e.get("repo", "").lower() or t == e.get("family", ""))
            words = set(re.findall(r"[\w-]+", desc(k).lower()))
            weak = sum(1 for t in toks if t in words)
            s = 3 * strong + weak
            if strong or weak >= max(2, len(toks)):   # name/repo/family hit, or the description mentions every topic word
                scored.append((s, k))
        scored.sort(reverse=True)
        print("topic matches (score, skill):", ", ".join(f"{s}:{k}" for s, k in scored[:60]) or "none")
        sel = {k for s, k in scored}
    if a.include_unregistered and not a.topic:
        sel |= set(unreg) if a.all else set()
    if not a.no_family:
        fams = {R[k]["family"] for k in sel if k in R and R[k].get("family")}
        added = {k for k in present if R[k].get("family") in fams} - sel
        if added:
            print(f"family members added (families update together; --no-family to skip): {', '.join(sorted(added))}")
            sel |= added
    removed = {k for k in sel if R.get(k, {}).get("removed_upstream")}
    if removed and not a.include_removed:
        print(f"skipped, removed upstream (use --include-removed to recheck): {', '.join(sorted(removed))}")
        sel -= removed
    if not sel:
        print("nothing selected"); return 1

    clones = find_clones({R[k]["repo"] for k in sel if k in R})
    by_repo = defaultdict(list)
    for k in sorted(sel):
        by_repo[R[k]["repo"] if k in R else "(unknown)"].append(k)
    shards, singles = [], []
    for repo, ks in sorted(by_repo.items()):
        if len(ks) == 1 and repo != "(unknown)":
            singles.append(ks[0]); continue
        for i in range(0, len(ks), a.max_per_shard):
            shards.append(ks[i:i + a.max_per_shard])
    for i in range(0, len(singles), 5):
        shards.append(singles[i:i + 5])
    print(f"\nSELECTED {len(sel)} skills -> {len(shards)} agents:")
    for i, s in enumerate(shards, 1):
        print(f"  s{i:02d}: {', '.join(s)}")
    if a.dry:
        print("(dry: nothing written)"); return 0

    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    scope = "all" if a.all else re.sub(r"[^a-z0-9]+", "-", (a.topic or a.skills or a.repo or "sel").lower())[:30].strip("-")
    run = Path(a.run_dir or H / ".agents/skill-update-runs" / f"{stamp}-{scope}").resolve()
    if " " in str(run):
        print("run dir must not contain spaces"); return 1
    for d in ("cards", "prompts", "results/problems", "snap", "work"):
        (run / d).mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL_DIR / "scripts", run / "tools", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(SKILL_DIR / "PROTOCOL.md", run / "PROTOCOL.md")
    lock = json.load(open(H / ".agents/.skill-lock.json")).get("skills", {}) if (H / ".agents/.skill-lock.json").exists() else {}
    heads = {c: sh(["git", "-C", c, "rev-parse", "HEAD"]) for c in clones}
    pins = {}
    if not a.no_pin:
        for repo in {R[k]["repo"] for k in sel if k in R}:
            out = sh(["git", "ls-remote", f"https://github.com/{repo}.git", "HEAD"])
            pins[repo] = out.split()[0] if out else None

    def canonical(k):
        ls = [l for l in locs[k] if not l["broken"]]
        for l in ls:
            if any(l["realpath"].startswith(c + os.sep) for c in clones):
                return l["realpath"]
        for l in ls:
            if "/.claude/skill-sources/" in l["realpath"]:
                return l["realpath"]
        if k in lock:
            for l in ls:
                if l["root"] == "agents" and l["kind"] == "dir":
                    return l["realpath"]
        for pref in ("agents", "claude", "codex", "hermes"):
            for l in ls:
                if l["root"] == pref and l["kind"] == "dir":
                    return l["realpath"]
        return ls[0]["realpath"] if ls else None

    manifest = []
    for i, ks in enumerate(shards, 1):
        sid = f"s{i:02d}"; card = {"agent_id": sid, "label": ", ".join(sorted({R.get(k, {}).get("repo", "?") for k in ks})), "skills": [],
                                    "paths": {"su": str(run), "work": str(run / "work" / sid), "results_file": str(run / "results" / f"{sid}.json"),
                                              "problems_dir": str(run / "results/problems"), "snap_dir": str(run / "snap"), "tools": str(run / "tools")}}
        for k in ks:
            can = canonical(k)
            if not can:
                print("skip (no readable local copy):", k); continue
            e = R.get(k, {}); tid, n = tree_id(Path(can))
            cl = next(((c, r, os.path.relpath(can, c)) for c, r in clones.items() if can.startswith(c + os.sep)), None)
            up = {"repo": e.get("repo", "(find the repo)"), "path": e.get("path") if e.get("path") is not None else (cl[2] if cl else None),
                  "confidence": "recorded" if e.get("confidence") == "verified" else "hint", "evidence": "skill-update registry" if e else "unregistered: identify by content",
                  "target_commit": pins.get(e.get("repo"))}
            locations = []
            for l in locs[k]:
                x = dict(l)
                ocl = next((c for c in clones if l["realpath"].startswith(c + os.sep)), None)
                if l["realpath"] == can:
                    x["relation"] = "is-canonical" if l["path"] == can else "symlink-to-canonical"
                elif l["broken"]:
                    x["relation"] = "broken-symlink"
                elif ocl and cl and ocl != cl[0]:
                    x["relation"] = "symlink-into-other-clone" if l["kind"] == "symlink" else "dir-inside-other-clone"
                else:
                    x["relation"] = "separate-copy" if l["kind"] == "dir" else "symlink-elsewhere"
                locations.append(x)
            gc = None
            if cl:
                others = [{"path": c2, "skill_dir": str(Path(c2) / cl[2]), "local_head": heads[c2], "dirty_files": None}
                          for c2, r2 in clones.items() if r2 == cl[1] and c2 != cl[0] and (Path(c2) / cl[2]).exists()]
                gc = {"path": cl[0], "origin": cl[1], "relpath": cl[2], "local_head": heads[cl[0]], "dirty_files": None, "other_clones": others}
            sk = {"name": k, "tier": 1 if up["confidence"] == "recorded" else 2, "upstream": up, "canonical": can, "canonical_tree_id": tid,
                  "file_count": n, "locations": locations, "registry": e,
                  "lock": ({**lock[k]} if k in lock else None), "git_clone": gc}
            card["skills"].append(sk); manifest.append({"shard": sid, **sk})
        (run / "cards" / f"{sid}.json").write_text(json.dumps(card, ensure_ascii=False, indent=1))
        notes = []
        for sk in card["skills"]:
            e = sk["registry"]
            if e.get("owner_edits"):
                notes.append(f"{sk['name']}: the owner keeps local edits here (e.g. a 'Media storage' paragraph) -> if upstream is newer the status is DIVERGED; build no snapshot, the orchestrator merges.")
            if e.get("last_hold_reason"):
                notes.append(f"{sk['name']}: last run it was held: {e['last_hold_reason'][:200]}")
            if not e:
                notes.append(f"{sk['name']}: NOT in the registry - identify the upstream by content (protocol 2.A) or answer NO_UPSTREAM.")
        prompt = (SKILL_DIR / "agent-prompt.txt").read_text().replace("{ID}", sid).replace("{SU}", str(run)).replace("{NOTES}", "\n".join("- " + x for x in notes) or "- none")
        (run / "prompts" / f"{sid}.txt").write_text(prompt)
    (run / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"\nRUN DIR: {run}\nprompts: {run}/prompts/*.txt  (one Agent per file)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
