#!/usr/bin/env python3
"""check_untouched.py - independent post-apply acceptance check for a skill-update run.
Fails if any file under the skill roots changed since the first apply log started but is not listed in the logs,
if an updated SKILL.md lost name/description, if an exec bit was lost, or if a new broken symlink appeared.
usage: check_untouched.py RUN"""
import datetime, json, os, re, sys
from pathlib import Path

RUN = Path(sys.argv[1]).resolve(); H = Path.home(); SELF = str(Path(__file__).resolve().parent.parent)
logs = [json.load(open(p)) for p in sorted(RUN.glob("apply-log-*.json"))]
if not logs:
    sys.exit("no apply logs in " + str(RUN))
start = min(datetime.datetime.fromisoformat(l["started"]).timestamp() for l in logs) - 5
expected, targets = set(), []
for l in logs:
    for e in l["skills"].values():
        for t in e["targets"]:
            targets.append(Path(t["path"]))
            expected |= {os.path.realpath(os.path.join(t["path"], r)) for r in t["w"] + t["d"]}
roots = [H / ".claude/skills", H / ".agents/skills", H / ".codex/skills", H / ".hermes/skills", H / ".claude/skill-sources", H / ".notfair", H / ".ponytail", H / ".codex/superpowers"]
unexpected = []
for r in roots:
    for p, ds, fs in os.walk(r):
        for f in fs:
            fp = os.path.join(p, f)
            try:
                m = os.lstat(fp).st_mtime
            except OSError:
                continue
            if m >= start and "/_backups/" not in fp and "/.git/" not in fp and "/skills/skill-update/" not in os.path.realpath(fp) and not f.endswith(".apply-tmp") and os.path.realpath(fp) not in expected:
                unexpected.append(fp.replace(str(H), "~"))
leftover = [str(p) for t in targets for p in t.rglob("*.apply-tmp")]
fm_bad = []
for t in set(targets):
    tx = (t / "SKILL.md").read_text(errors="ignore")[:4000] if (t / "SKILL.md").exists() else ""
    m = re.match(r"^---\s*\n(.*?)\n---", tx, re.S)
    if not m or "name:" not in m.group(1) or "description:" not in m.group(1):
        fm_bad.append(str(t))
broken = [str(e) for rt in (".claude/skills", ".agents/skills", ".codex/skills") if (H / rt).is_dir()
          for e in (H / rt).iterdir() if e.is_symlink() and not e.exists() and os.lstat(e).st_mtime >= start]
print(f"targets: {len(set(targets))} | unexpected changed files: {len(unexpected)} | leftover temp files: {len(leftover)} | "
      f"bad SKILL.md frontmatter: {len(fm_bad)} | new broken symlinks: {len(broken)}")
for x in (unexpected + leftover + fm_bad + broken)[:20]:
    print("  -", x)
sys.exit(1 if (unexpected or leftover or fm_bad or broken) else 0)
