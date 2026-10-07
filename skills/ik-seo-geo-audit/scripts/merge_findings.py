#!/usr/bin/env python3
"""merge_findings.py — collect the findings tables of all auditor reports into one CSV.

usage: merge_findings.py --audits DIR --out raw-findings.csv
A table row is taken when the table header starts with 'URL' and contains 'issue'. Escaped pipes (\\|) are kept.
"""
import argparse, csv, glob, os, re

ap = argparse.ArgumentParser(); ap.add_argument("--audits", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
rows = []
for f in sorted(glob.glob(os.path.join(a.audits, "*.md"))):
    agent = os.path.basename(f)[:-3]
    hdr = None
    for ln in open(f, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not (ln.startswith("|") and ln.count("|") >= 5):
            hdr = None if ln.strip() and not ln.startswith("|") else hdr
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", ln.strip())[1:-1]]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        low = [c.lower() for c in cells]
        if low and low[0].startswith("url") and any("issue" in c or "пробл" in c or "проблем" in c for c in low):
            hdr = low; continue
        if hdr and len(cells) >= 5:
            rows.append([agent] + cells[:5])
with open(a.out, "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo); w.writerow(["agent", "url", "issue", "evidence", "severity_guess", "skill_rule"]); w.writerows(rows)
from collections import Counter
print(len(rows), "findings from", len(set(r[0] for r in rows)), "reports;", dict(Counter(r[0] for r in rows)))
