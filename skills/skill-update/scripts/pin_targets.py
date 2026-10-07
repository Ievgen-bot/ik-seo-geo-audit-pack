#!/usr/bin/env python3
"""Pin one target commit per upstream repo into cards/*.json and manifest.json (git ls-remote only; read-only).
usage: pin_targets.py SU [--skip s1,pt]"""
import json, subprocess, sys, datetime, re
from pathlib import Path

su = Path(sys.argv[1]).resolve()
skip = set((sys.argv[sys.argv.index("--skip") + 1] if "--skip" in sys.argv else "").split(","))
cards = {p.stem: json.load(open(p)) for p in sorted((su / "cards").glob("*.json"))}
pins = {}
for cid, c in cards.items():
    if cid in skip:
        continue
    for s in c["skills"]:
        repo = s["upstream"]["repo"]
        if repo in pins or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo or ""):
            continue
        r = subprocess.run(["git", "ls-remote", f"https://github.com/{repo}.git", "HEAD"], capture_output=True, text=True, timeout=30,
                           env={"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/bin:/opt/homebrew/bin"})
        pins[repo] = r.stdout.split()[0] if r.returncode == 0 and r.stdout.strip() else None
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
for cid, c in cards.items():
    if cid in skip:
        continue
    for s in c["skills"]:
        t = pins.get(s["upstream"]["repo"])
        if t:
            s["upstream"]["target_commit"] = t; s["upstream"]["target_pinned_at"] = now
    json.dump(c, open(su / "cards" / f"{cid}.json", "w"), ensure_ascii=False, indent=1)
man = json.load(open(su / "manifest.json"))
for m in man:
    if m["shard"] in skip:
        continue
    t = pins.get(m["upstream"]["repo"])
    if t:
        m["upstream"]["target_commit"] = t; m["upstream"]["target_pinned_at"] = now
json.dump(man, open(su / "manifest.json", "w"), ensure_ascii=False, indent=1)
for repo, t in sorted(pins.items()):
    print(f"{repo:42s} {t[:10] if t else 'NOT FOUND (hint repo must be resolved by the agent)'}")
