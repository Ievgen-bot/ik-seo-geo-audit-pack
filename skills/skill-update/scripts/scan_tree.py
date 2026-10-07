#!/usr/bin/env python3
"""Static security scan of a skill tree. Reads files as TEXT/bytes only; never executes anything from the tree.

usage: scan_tree.py NEW_DIR [--old OLD_DIR] [--json OUT.json] [--top N]

Findings carry severity HIGH/MEDIUM/LOW and, when --old is given, status new|pre-existing.
Snippets are redacted for secret-like content. The scanner is a signal generator: a human/agent must triage.
"""
import argparse, json, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path

JUNK_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".avif", ".mp3", ".mp4", ".mov", ".wav", ".ogg", ".webm", ".m4a",
             ".woff", ".woff2", ".ttf", ".otf", ".eot", ".pdf", ".tiff", ".heic"}
EXEC_BIN_EXT = {".node", ".so", ".dylib", ".exe", ".dll", ".dmg", ".pkg", ".msi", ".jar", ".class", ".pyd", ".scr", ".app"}
ARCHIVE_EXT = {".wasm", ".whl", ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2", ".xz", ".egg"}
SCRIPT_EXT = {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".ps1", ".bat", ".cmd", ".php"}
MAX_TEXT = 3_000_000
MAGIC = [(b"\xcf\xfa\xed\xfe", "Mach-O"), (b"\xce\xfa\xed\xfe", "Mach-O"), (b"\xfe\xed\xfa\xcf", "Mach-O"),
         (b"\xca\xfe\xba\xbe", "Mach-O/Java class"), (b"\x7fELF", "ELF")]

R = lambda p, f=re.I: re.compile(p, f)
RULES = [  # (id, severity, regex, description)
    ("H01-pipe-to-shell", "HIGH", R(r"\b(curl|wget|iwr|Invoke-WebRequest)\b[^\n]{0,200}?\|\s*(sudo\s+)?(?:ba|z|da|k)?sh\b"), "download piped into a shell"),
    ("H01-pipe-to-interp", "HIGH", R(r"\b(curl|wget)\b[^\n|]{0,200}\|\s*(python3?|node|perl|ruby|php)\b"), "download piped into an interpreter"),
    ("H01-process-subst", "HIGH", R(r"\b(bash|sh|zsh|source|\.)\s+<\(\s*(curl|wget)|sh\s+-c\s+[\"']\$\(\s*(curl|wget)"), "remote script run via process substitution"),
    ("H02-decode-exec", "HIGH", R(r"base64\s+(-d|--decode|-D)[^\n]{0,100}\|\s*(ba|z)?sh|\beval\s*\(?\s*[\"'`$(][^\n]{0,80}(base64|atob|decode)|\bexec\s*\(\s*(base64|codecs|zlib|marshal)|Function\(\s*atob|eval\(\s*String\.fromCharCode|python3?\s+-c\s+['\"][^'\"\n]{0,80}(base64|exec\(|eval\()"), "decode-then-execute pattern"),
    ("H03-destructive-rm", "HIGH", R(r"\brm\s+(-[a-zA-Z]+\s+)*-[a-zA-Z]*[rR][a-zA-Z]*\s+(-[a-zA-Z]+\s+)*(/\s|/\*|~/?(\s|$|\*)|\$HOME/?(\s|$|\*)|\$\{HOME\}|\"\$HOME\")|shutil\.rmtree\(\s*(Path\.home|os\.path\.expanduser|['\"]/['\"])|find\s+(/|~|\$HOME)\s[^\n]{0,80}-delete|\bmkfs\.|dd\s+if=[^\n]{0,60}of=/dev/|:\(\)\s*\{\s*:\|:&\s*\};:"), "destructive filesystem command"),
    ("H04-reverse-shell", "HIGH", R(r"/dev/tcp/|bash\s+-i\s*>?&|\bnc(at)?\s+(-[a-z]+\s+)*-[a-z]*e\s|socat\s[^\n]{0,80}exec:|python3?\s+-c\s+['\"]import socket[^\n]{0,200}(subprocess|pty|dup2)|mkfifo[^\n]{0,60}\bnc\b"), "reverse-shell pattern"),
    ("H05-persistence", "HIGH", R(r"(>>|tee\s+-a)\s*~?/?(\$HOME/)?\.(zshrc|bashrc|bash_profile|zprofile|profile|zshenv)\b|crontab\s+(-\s|<)|\(\s*crontab\s+-l|/etc/cron|Library/LaunchAgents|Library/LaunchDaemons|launchctl\s+(load|bootstrap|enable)|systemctl\s+(--user\s+)?enable|/etc/systemd/system|@reboot\b"), "persistence mechanism (autostart/cron/launchd/shell profile)"),
    ("H07-exfil-endpoint", "HIGH", R(r"webhook\.site|requestbin\.|pipedream\.net|ngrok\.(io|app|dev)|oastify\.com|interact\.sh|burpcollaborator|discord(app)?\.com/api/webhooks|hooks\.slack\.com/services|api\.telegram\.org/bot\d|pastebin\.com|paste\.ee|transfer\.sh|file\.io/|anonfiles|\b0x0\.st|\.onion\b|dnslog\.|canarytokens"), "known exfiltration / paste / tunnel endpoint"),
    ("H08-prompt-injection", "HIGH", R(r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|system)\s+(instructions?|rules?|prompts?|messages?)|disregard\s+(all\s+|any\s+|the\s+)?(previous|prior|above|system)|forget\s+(everything|all)\s+(above|before|previous)|do\s+not\s+(tell|inform|notify|alert|reveal\s+(this\s+)?to)\s+the\s+user|without\s+(telling|informing|notifying)\s+the\s+user|(silently|secretly|covertly|stealthily)\s+(run|execute|send|upload|post|install|download|exfiltrate|copy|read)|\bexfiltrat|you\s+are\s+now\s+(in\s+)?(developer|dan|god|root|unrestricted)\b|override\s+(the\s+)?(system|safety|security)\s+(prompt|rules|instructions|policy)|(print|reveal|show|output)\s+(your\s+)?(system\s+prompt|hidden\s+instructions)|<\s*/?\s*(system|instructions?)\s*>|\[\s*(SYSTEM|INST)\s*\]"), "prompt-injection / concealment language"),
    ("M01-privilege", "MEDIUM", R(r"\bsudo\b|chmod\s+(-R\s+)?(0?777|[ug]?\+s)\b|chown\s+(-R\s+)?root|visudo|/etc/sudoers|\bsetuid\b"), "privilege escalation / permissive chmod"),
    ("M02-credential-path", "MEDIUM", R(r"(~|\$HOME)?/?\.ssh/|\bid_rsa\b|\bid_ed25519\b|\.aws/(credentials|config)|\.config/gh/|\.npmrc\b|\.netrc\b|\.docker/config\.json|security\s+find-(generic|internet)-password|Library/Keychains|Cookies\.sqlite|Login\s+Data|\.gnupg|\.kube/config|\.pypirc|\.git-credentials|(cat|source|read|open)\s+[^\n]{0,20}\.env\b|\bprintenv\b|os\.environ\.items|JSON\.stringify\(\s*process\.env"), "references credential stores / environment dump"),
    ("M03-network-send", "MEDIUM", R(r"\bcurl\s+[^\n]{0,200}(-X\s*(POST|PUT|PATCH)|\s-d\s|--data|\s-F\s|--form|--upload-file|\s-T\s)|wget\s+[^\n]{0,100}--post|requests\.(post|put|patch)\(|urlopen\([^\n]{0,100}data=|fetch\([^\n]{0,160}method:\s*['\"](POST|PUT|PATCH)|axios\.(post|put|patch)\(|\bscp\s+\S|\brsync\s[^\n]{0,80}@|\bsftp\s"), "sends data over the network"),
    ("M04-runtime-install", "MEDIUM", R(r"\bpip3?\s+install\b|\bnpm\s+(i|install|add)\b|\bnpx\s+(-y\s+|--yes\s+)?[@a-z]|\bpnpm\s+(dlx|add)\b|\byarn\s+(dlx|add|global)\b|\bbrew\s+install\b|\buvx?\s+(tool\s+install|pip\s+install|run)\b|\bgo\s+install\b|\bcargo\s+install\b|\bgem\s+install\b|\bapt(-get)?\s+install\b"), "installs/executes packages at runtime"),
    ("M05-obfuscation", "MEDIUM", R(r"[A-Za-z0-9+/]{240,}={0,2}|\b[0-9a-fA-F]{240,}\b|(\\x[0-9a-fA-F]{2}){16,}|chr\(\d+\)\s*\+\s*chr\(\d+\)"), "long encoded blob / obfuscation"),
    ("M06-secret-literal", "MEDIUM", R(r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|\bsk-[A-Za-z0-9_-]{32,}|sk_live_[A-Za-z0-9]+|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"), "secret-like literal (content redacted)"),
    ("M07-agent-bypass", "MEDIUM", R(r"--dangerously-skip-permissions|bypassPermissions|--yolo\b|dangerouslyDisableSandbox|--no-sandbox|--allow-all-tools|--trust-all|always-approve|auto-approve"), "disables agent safety/permission prompts"),
    ("M08-remote-instructions", "MEDIUM", R(r"(fetch|download|load|read|curl|wget)\s+[^\n]{0,60}(instructions?|prompts?|rules|skill)\s+from\s+https?://"), "loads instructions from a remote URL at runtime"),
    ("L01-dynamic-exec", "LOW", R(r"\beval\s*\(|\bexec\s*\(|os\.system\(|subprocess\.[A-Za-z]+\([^\n]{0,80}shell\s*=\s*True|child_process\.exec(Sync)?\("), "dynamic code/shell execution in code"),
]
HTML_COMMENT = re.compile(r"<!--(.{20,}?)-->", re.S)
HTML_IMPERATIVE = re.compile(r"\b(run|execute|curl|ignore|send|post|upload|do not|don't tell|secret)\b", re.I)
ZW_RE = re.compile("[​-‏⁠-⁤﻿]")
BIDI_RE = re.compile("[‪-‮⁦-⁩]|[\U000e0000-\U000e007f]")
CRED_RE = RULES[[r[0] for r in RULES].index("M02-credential-path")][2]
NET_RE = RULES[[r[0] for r in RULES].index("M03-network-send")][2]
REDACT = [re.compile(RULES[[r[0] for r in RULES].index("M06-secret-literal")][2].pattern),
          re.compile(r"(?i)(bearer\s+[A-Za-z0-9._~+/-]{8,}|password\s*[:=]\s*\S+|passwd\s*[:=]\s*\S+|token\s*[:=]\s*\S+|api[_-]?key\s*[:=]\s*\S+|secret\s*[:=]\s*\S+)")]
URL_RE = re.compile(r"https?://([A-Za-z0-9.-]+)")


def redact(s: str) -> str:
    for r in REDACT:
        s = r.sub("[REDACTED]", s)
    return s


def snippet(text: str, start: int, end: int) -> str:
    ls = text.rfind("\n", 0, start) + 1
    le = text.find("\n", end)
    le = len(text) if le < 0 else le
    return redact(re.sub(r"\s+", " ", text[ls:le]).strip())[:140]


def iter_files(root: Path):
    for p, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in JUNK_DIRS)
        for f in sorted(files):
            if f == ".DS_Store" or f.startswith("._"):
                continue
            yield Path(p) / f
        for d in list(dirs):  # symlinked dirs are not descended; report them
            dp = Path(p) / d
            if dp.is_symlink():
                yield dp


def scan(root: Path):
    findings, domains, inv = [], Counter(), Counter()
    exec_bits, scripts = [], []
    root = root.resolve()
    for fp in iter_files(root):
        rel = str(fp.relative_to(root))
        ext = fp.suffix.lower()
        if fp.is_symlink():
            tgt = os.readlink(fp)
            real = os.path.realpath(fp)
            if os.path.isabs(tgt) or not (real == str(root) or real.startswith(str(root) + os.sep)):
                findings.append({"id": "H12-symlink-escape", "severity": "HIGH", "file": rel, "line": 0, "snippet": f"symlink -> {tgt[:100]}", "desc": "symlink points outside the skill tree"})
            continue
        try:
            st = fp.stat(); size = st.st_size
        except OSError:
            continue
        inv[ext or "(none)"] += 1
        if st.st_mode & 0o111:
            exec_bits.append(rel)
        if ext in SCRIPT_EXT:
            scripts.append(rel)
        if ext in MEDIA_EXT:
            continue
        try:
            head = fp.open("rb").read(4096)
        except OSError:
            continue
        magic = next((n for m, n in MAGIC if head.startswith(m)), None)
        is_bin = b"\x00" in head
        if ext in EXEC_BIN_EXT or magic or (head[:2] == b"MZ" and ext in {".exe", ".dll", ".scr", ""} and is_bin):
            findings.append({"id": "H10-executable-binary", "severity": "HIGH", "file": rel, "line": 0, "snippet": f"{magic or ext or 'binary'} {size} bytes", "desc": "native executable/library inside a skill"})
            continue
        if ext in ARCHIVE_EXT:
            findings.append({"id": "M09-archive-or-wasm", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": f"{ext} {size} bytes", "desc": "opaque archive / wasm inside a skill"})
            continue
        if is_bin:
            findings.append({"id": "M10-unknown-binary", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": f"{size} bytes", "desc": "binary file of unknown type"})
            continue
        if size > MAX_TEXT:
            findings.append({"id": "M11-large-unscanned", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": f"{size} bytes text", "desc": "large text file not scanned"})
            continue
        try:
            text = fp.read_text(errors="replace")
        except OSError:
            continue
        # per-file rule scan, max 3 hits per rule per file
        for rid, sev, rx, desc in RULES:
            if rid.startswith("M05") and ext in {".json", ".svg", ".lock", ".map"} or (rid.startswith("M05") and ".min." in rel):
                continue
            hits = 0
            for m in rx.finditer(text):
                if rid.startswith("M05") and len(text.splitlines()) > 0 and re.fullmatch(r"[A-Za-z]+", m.group(0)):
                    continue
                findings.append({"id": rid, "severity": sev, "file": rel, "line": text.count("\n", 0, m.start()) + 1,
                                 "snippet": "(redacted)" if rid.startswith("M06") else snippet(text, m.start(), m.end()), "desc": desc})
                hits += 1
                if hits >= 3:
                    break
        # hidden unicode
        bidi = BIDI_RE.findall(text); zw = [z for z in ZW_RE.findall(text)]
        if text.startswith("﻿"):
            zw = zw[1:]
        if bidi:
            findings.append({"id": "H09-bidi-or-tag-chars", "severity": "HIGH", "file": rel, "line": 0, "snippet": f"{len(bidi)} chars", "desc": "bidi-override / Unicode tag characters (can hide text)"})
        if len(zw) >= 5:
            findings.append({"id": "H09-zero-width", "severity": "HIGH", "file": rel, "line": 0, "snippet": f"{len(zw)} chars", "desc": "many zero-width characters (can hide text)"})
        elif zw:
            findings.append({"id": "M12-zero-width", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": f"{len(zw)} chars", "desc": "zero-width characters"})
        # hidden html comments with imperative language
        for m in HTML_COMMENT.finditer(text):
            if HTML_IMPERATIVE.search(m.group(1)):
                findings.append({"id": "M13-html-comment-instruction", "severity": "MEDIUM", "file": rel, "line": text.count("\n", 0, m.start()) + 1, "snippet": redact(re.sub(r"\s+", " ", m.group(1))[:140]), "desc": "HTML comment with imperative language (hidden from rendered markdown)"})
                break
        # credential path + network send in the same file
        if CRED_RE.search(text) and NET_RE.search(text):
            findings.append({"id": "H06-cred-plus-network", "severity": "HIGH", "file": rel, "line": 0, "snippet": "credential-store reference and network send in one file", "desc": "possible credential exfiltration (verify)"})
        # svg/html scripts
        if ext in {".svg", ".html", ".htm"} and re.search(r"<script\b|\son\w+\s*=", text, re.I):
            findings.append({"id": "M14-inline-script", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": "script/event handler in " + ext, "desc": "active content in svg/html"})
        # package.json lifecycle scripts, setup.py, .pth
        if fp.name == "package.json":
            try:
                scripts_obj = (json.loads(text).get("scripts") or {})
            except Exception:
                scripts_obj = {}
            for k, v in scripts_obj.items():
                if k in {"preinstall", "install", "postinstall", "prepare", "prepublish", "prepack"}:
                    bad = bool(re.search(r"curl|wget|node\s+-e|eval|base64|sh\s+-c|powershell|https?://", str(v), re.I))
                    findings.append({"id": "H11-lifecycle-script", "severity": "HIGH" if bad else "MEDIUM", "file": rel, "line": 0, "snippet": redact(f"{k}: {str(v)[:100]}"), "desc": "npm lifecycle script runs on install"})
        if fp.name == "setup.py" and re.search(r"cmdclass|os\.system|subprocess|exec\(|urllib|requests", text):
            findings.append({"id": "M15-setup-py-exec", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": "setup.py runs code", "desc": "setup.py with command/network code"})
        if ext == ".pth":
            findings.append({"id": "H11-pth-file", "severity": "HIGH", "file": rel, "line": 0, "snippet": ".pth", "desc": ".pth files execute code at interpreter start"})
        if fp.name == ".gitmodules":
            findings.append({"id": "M16-submodule", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": ".gitmodules", "desc": "pulls external code via git submodule"})
        # SKILL.md frontmatter risks
        if fp.name == "SKILL.md":
            fm = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
            if fm:
                body = fm.group(1)
                m = re.search(r"(?m)^allowed-tools\s*:\s*(.+)$", body)
                if m and re.search(r"Bash(?!\()|Bash\(\*\)|(^|[\s,\[])\*($|[\s,\]])", m.group(1)):
                    findings.append({"id": "M17-allowed-tools-broad", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": redact(m.group(0)[:120]), "desc": "frontmatter grants broad tool access"})
                if re.search(r"(?m)^hooks\s*:", body):
                    findings.append({"id": "M18-frontmatter-hooks", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": "hooks: in frontmatter", "desc": "frontmatter registers hooks (auto-run code)"})
        if fp.name in {"settings.json", "settings.local.json", ".mcp.json", "hooks.json", "plugin.json"} and re.search(r'"(hooks|mcpServers|command)"', text):
            findings.append({"id": "M19-hooks-or-mcp-config", "severity": "MEDIUM", "file": rel, "line": 0, "snippet": fp.name, "desc": "config that registers hooks / MCP servers / commands"})
        for m in URL_RE.finditer(text):
            domains[m.group(1).lower().rstrip(".")] += 1
    return findings, domains, inv, exec_bits, scripts


def fp_key(f):
    return (f["id"], f["file"], re.sub(r"\W+", "", f.get("snippet", ""))[:80])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("new"); ap.add_argument("--old"); ap.add_argument("--json"); ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args()
    nf, dom, inv, ex, scr = scan(Path(a.new))
    old_keys = None
    if a.old and Path(a.old).is_dir():
        of, *_ = scan(Path(a.old)); old_keys = {fp_key(f) for f in of}
    for f in nf:
        f["status"] = ("pre-existing" if fp_key(f) in old_keys else "new") if old_keys is not None else "no-baseline"
    sev_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    nf.sort(key=lambda f: (sev_rank[f["severity"]], f["status"] != "new", f["file"], f["line"]))
    cnt = Counter(f["severity"] for f in nf); cnt_new = Counter(f["severity"] for f in nf if f["status"] == "new")
    out = {"root": str(Path(a.new)), "baseline": a.old, "files_by_ext": dict(inv.most_common(15)), "scripts": scr[:60], "exec_bit_files": ex[:60],
           "domains": dict(dom.most_common(40)), "counts": dict(cnt), "counts_new": dict(cnt_new), "findings": nf}
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"scan {a.new}: files={sum(inv.values())} scripts={len(scr)} exec_bit={len(ex)} | HIGH={cnt.get('HIGH', 0)} MEDIUM={cnt.get('MEDIUM', 0)} LOW={cnt.get('LOW', 0)}"
          + (f" | NEW: HIGH={cnt_new.get('HIGH', 0)} MEDIUM={cnt_new.get('MEDIUM', 0)}" if old_keys is not None else " | (no baseline)"))
    for f in [x for x in nf if x["severity"] != "LOW"][:a.top]:
        print(f"  {f['severity'][:4]} {f['status'][:4]} {f['id']} {f['file']}:{f['line']} :: {f['snippet'][:100]}")
    if dom:
        print("  domains:", ", ".join(f"{d}({c})" for d, c in dom.most_common(12)))


if __name__ == "__main__":
    main()
