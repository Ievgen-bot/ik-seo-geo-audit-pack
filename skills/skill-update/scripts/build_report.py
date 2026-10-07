#!/usr/bin/env python3
"""Build RESULTS.tsv and PROBLEMS.md (Ukrainian) from manifest.json + results/*.json.
Agent-written text is untrusted data: it is sanitised (control/format chars removed) and truncated; full per-skill
problem files stay on disk and are only linked.
usage: build_report.py SU OUT_DIR [--apply-log apply-log.json]"""
import json, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from resultslib import load_results

su, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
applied = {}
if "--apply-log" in sys.argv:
    lg = json.load(open(sys.argv[sys.argv.index("--apply-log") + 1]))
    applied = {k: v for k, v in lg.get("skills", {}).items()}
man = {m["name"]: m for m in json.load(open(su / "manifest.json"))}
res = load_results(su)


def clean(s, n=300):
    s = "".join(ch for ch in str(s or "") if ch in "\n " or unicodedata.category(ch)[0] not in "CZ" or ch == " ")
    s = re.sub(r"\s+", " ", s).strip()
    return (s[: n - 1] + "…") if len(s) > n else s


def ver(r):
    v = r.get("versions") or {}
    a = (v.get("installed_commit") or "?")[:8]; b = (v.get("latest_commit") or "?")[:8]
    return f"{a} ({clean(v.get('installed_date'), 10)}) → {b} ({clean(v.get('latest_date'), 10)})"


STATUS_UA = {"UPDATED": "оновлено", "UPDATE_READY": "оновлено/готове до оновлення", "UP_TO_DATE": "вже актуальний", "FLAGGED_UNSAFE": "НЕБЕЗПЕЧНИЙ — не оновлено",
             "FLAGGED_REVIEW": "потрібна ручна перевірка — не оновлено", "DIVERGED": "локальні правки — не оновлено",
             "REMOVED_UPSTREAM": "upstream видалив/об'єднав скіл — не оновлено", "NO_UPSTREAM": "upstream не знайдено (імовірно власний)",
             "ERROR": "помилка перевірки", "NOT_AUDITED": "не перевірено"}
with open(out / "RESULTS.tsv", "w") as f:
    f.write("skill\tshard\ttier\tupstream\tstatus\tsecurity\tinstalled->latest\tapplied\n")
    for k, m in sorted(man.items()):
        r = res.get(k, {"status": "NOT_AUDITED"})
        f.write("\t".join([k, m["shard"], str(m["tier"]), clean(f"{m['upstream']['repo']}:{m['upstream'].get('path') or ''}", 80), r["status"],
                           (r.get("security") or {}).get("verdict", ""), ver(r) if r.get("versions") else "", "yes" if k in applied else ""]) + "\n")

cats = [("FLAGGED_UNSAFE", "🔴 Небезпечні — НЕ оновлювати"), ("FLAGGED_REVIEW", "🟠 Потрібна ручна перевірка — не оновлено"),
        ("DIVERGED", "🟡 Є локальні правки — оновлення їх затре, не оновлено"), ("REMOVED_UPSTREAM", "🟡 Upstream видалив або об'єднав скіл — не оновлено"),
        ("NO_UPSTREAM", "⚪ Upstream не знайдено (імовірно власні скіли)"), ("ERROR", "⚫ Не вдалося перевірити")]
by = defaultdict(list)
for k in man:
    by[res.get(k, {"status": "NOT_AUDITED"})["status"]].append(k)
L = ["# Скіли, які НЕ варто оновлювати автоматично", "",
     f"Перевірено: {len(res)} з {len(man)} скілів у маніфесті. Нижче лише ті, що потребують вашого рішення. Причини скорочені з файлів `results/problems/<скіл>.md` (там повний опис, знахідки й що можна зробити).", ""]
def ua_reason(k, r):
    """Prefer the Ukrainian 'Чому не оновлено' line of the skill's problem file; fall back to structured fields."""
    f = su / "results/problems" / f"{k}.md"
    if f.exists():
        for line in f.read_text(errors="ignore").splitlines():
            if line.startswith("- Чому не оновлено:"):
                return clean(line.split(":", 1)[1], 520)
    hold = r.get("orchestrator_hold") or {}
    s_ = r.get("security") or {}
    return clean(hold.get("reason") or s_.get("reasoning") or (r.get("diff") or {}).get("summary") or "; ".join(r.get("notes") or []), 420)


for st, title in cats + [("NOT_AUDITED", "⚫ Не перевірено")]:
    ks = sorted(by.get(st, []))
    if not ks:
        continue
    L += [f"## {title} ({len(ks)})", ""]
    for k in ks:
        r = res.get(k, {}); u = r.get("upstream") or {}
        L += [f"### `{k}`", f"- Джерело: `{clean(u.get('repo') or man[k]['upstream']['repo'], 80)}` (`{clean(u.get('path') or man[k]['upstream'].get('path') or '', 80)}`)"]
        if r.get("versions"):
            L.append(f"- Версії: {ver(r)}")
        L.append(f"- Причина: {ua_reason(k, r)}")
        if (su / "results/problems" / f"{k}.md").exists():
            L.append(f"- Деталі: `results/problems/{k}.md`")
        L.append("")
(out / "PROBLEMS.md").write_text("\n".join(L))
tot = {st: len(v) for st, v in by.items()}
print("RESULTS.tsv + PROBLEMS.md written to", out, "|", tot)
