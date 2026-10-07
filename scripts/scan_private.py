#!/usr/bin/env python3
"""scan_private.py — refuse to publish when the repository contains secrets or private data.

usage: scan_private.py [ROOT]          exit 0 = clean, 1 = hits (printed masked, file:line)
Checks every file except .git/: secret-like literals, personal paths, e-mails, phone numbers, IPv4 addresses,
plus the user's private deny-list (one case-insensitive substring per line) from
~/.config/ik-seo-geo-audit/private-patterns.txt — that list lives OUTSIDE the repo on purpose.
"""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
DENY = Path.home() / ".config" / "ik-seo-geo-audit" / "private-patterns.txt"
ALLOW_EMAIL = re.compile(r"@(example\.(com|org)|users\.noreply\.github\.com|anthropic\.com)$", re.I)
CHECKS = [
    ("secret", re.compile(r"(sk_live_[0-9a-zA-Z]{8,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")),
    ("secret", re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{20,}")),
    ("secret", re.compile(r"(?i)\b(api[_-]?key|token|password|passwd|secret)\b\s*[=:]\s*['\"][^'\"\s]{8,}['\"]")),
    ("personal path", re.compile(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|CloudStorage/GoogleDrive|My Drive/|Мій диск")),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone", re.compile(r"(?<![\w.])\+\d[\d\s().-]{8,}\d")),
    ("ipv4", re.compile(r"(?<![\d.])(?!127\.0\.0\.1|0\.0\.0\.0)(\d{1,3}\.){3}\d{1,3}(?![\d.])")),
]
deny = []
if DENY.exists():
    deny = [l.strip().lower() for l in DENY.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]

def mask(s):
    s = s.strip()
    return (s[:4] + "…" + s[-2:]) if len(s) > 8 else "…"

hits = 0
for f in sorted(ROOT.rglob("*")):
    if ".git" in f.parts or not f.is_file() or f.stat().st_size > 2_000_000:
        continue
    try:
        text = f.read_text(encoding="utf-8")
    except Exception:
        continue
    rel = f.relative_to(ROOT)
    if rel.as_posix() == "scripts/scan_private.py":  # the scanner's own pattern definitions
        continue
    for n, line in enumerate(text.splitlines(), 1):
        for kind, rx in CHECKS:
            for m in rx.finditer(line):
                val = m.group(0)
                if kind == "email" and ALLOW_EMAIL.search(val):
                    continue
                if kind == "ipv4" and re.fullmatch(r"\d+\.\d+\.\d+(\.\d+)?", val) and rel.suffix in (".json",) and "version" in line.lower():
                    continue
                print(f"{rel}:{n}: {kind}: {mask(val)}"); hits += 1
        low = line.lower()
        for d in deny:
            if d in low:
                print(f"{rel}:{n}: private pattern #{deny.index(d)+1}"); hits += 1
print(f"scan: {'CLEAN' if hits == 0 else str(hits) + ' hit(s)'} ({len(deny)} private patterns loaded)")
sys.exit(1 if hits else 0)
