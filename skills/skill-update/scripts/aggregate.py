#!/usr/bin/env python3
"""Aggregate audit results: coverage vs manifest, status counts, flagged list. Read-only.
usage: aggregate.py SU [--md OUT.md]"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from resultslib import load_results

su = Path(sys.argv[1]).resolve()
man = {m["name"]: m for m in json.load(open(su / "manifest.json"))}
res = load_results(su); files = defaultdict(list)
for k, r in res.items(): files[k].append(r.get('_file', ''))
shards = {m["shard"] for m in man.values()}
missing = sorted(set(man) - set(res)); extra = sorted(set(res) - set(man)); dup = sorted(k for k, v in files.items() if len(v) > 1)
print(f"manifest skills: {len(man)} | with result: {len(res)} | missing: {len(missing)} | unknown: {len(extra)} | duplicated: {len(dup)}")
if missing: print("  MISSING:", ", ".join(missing[:40]))
cnt = Counter(r["status"] for r in res.values())
print("status:", dict(cnt))
bad = []
for k, r in res.items():
    st = r["status"]
    if st == "UPDATE_READY":
        sn = r.get("snapshot") or {}
        if (r.get("security") or {}).get("verdict") != "SAFE" or not Path(sn.get("dir", "/nonexistent")).is_dir():
            bad.append(f"{k}: UPDATE_READY without SAFE verdict/snapshot")
    if st in ("FLAGGED_UNSAFE", "FLAGGED_REVIEW", "DIVERGED", "REMOVED_UPSTREAM", "NO_UPSTREAM", "ERROR") and not (su / "results/problems" / f"{k}.md").exists():
        bad.append(f"{k}: {st} without problem file")
if bad: print("  INCONSISTENT:"); [print("   -", b) for b in bad]
by = defaultdict(list)
for k, r in res.items(): by[r["status"]].append(k)
for st in ("UPDATED", "UPDATE_READY", "UP_TO_DATE", "FLAGGED_UNSAFE", "FLAGGED_REVIEW", "DIVERGED", "REMOVED_UPSTREAM", "NO_UPSTREAM", "ERROR"):
    if by.get(st): print(f"  {st} ({len(by[st])}): {', '.join(sorted(by[st]))[:600]}")
if "--md" in sys.argv:
    out = Path(sys.argv[sys.argv.index("--md") + 1])
    lines = ["# Підсумок аудиту скілів", "", f"Скілів у маніфесті: {len(man)}, з вердиктом: {len(res)}.", ""]
    for st, title in (("UPDATED", "Оновлено"), ("UPDATE_READY", "Безпечні, готові до оновлення"), ("UP_TO_DATE", "Вже актуальні"), ("FLAGGED_UNSAFE", "НЕБЕЗПЕЧНІ — не оновлювати"),
                      ("FLAGGED_REVIEW", "Потрібна ручна перевірка — не оновлено"), ("DIVERGED", "Локальні правки — не оновлено"), ("REMOVED_UPSTREAM", "Upstream видалив/об'єднав скіл — не оновлено"),
                      ("NO_UPSTREAM", "Upstream не знайдено (імовірно власні)"), ("ERROR", "Помилки перевірки")):
        if by.get(st):
            lines += [f"## {title} ({len(by[st])})", ""] + [f"- `{k}`" for k in sorted(by[st])] + [""]
    out.write_text("\n".join(lines)); print("written", out)
