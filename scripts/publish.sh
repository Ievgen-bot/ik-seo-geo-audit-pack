#!/usr/bin/env bash
# publish.sh — release this pack: privacy scan -> version bump -> CHANGELOG -> validate -> commit -> tag -> (push)
# usage: scripts/publish.sh <patch|minor|major|--initial> "what changed (one line per change, separated by ';')" [--push]
# Refuses to continue on any scan hit. Pushing is done only with --push.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BUMP="${1:?patch|minor|major|--initial}"; MSG="${2:?message}"; PUSH="${3:-}"

case "$(git config user.email)" in *@users.noreply.github.com) ;; *) echo "STOP: set a GitHub noreply author first (git config user.email <id>+<login>@users.noreply.github.com) — a machine e-mail would be published in the history."; exit 1;; esac
python3 scripts/scan_private.py "$ROOT" || { echo "STOP: privacy/secret scan failed — nothing was committed."; exit 1; }

OLD="$(cat VERSION)"
if [ "$BUMP" = "--initial" ]; then NEW="$OLD"; else
  NEW="$(python3 - "$OLD" "$BUMP" <<'PY'
import sys
ma, mi, pa = map(int, sys.argv[1].split("."))
b = sys.argv[2]
print(f"{ma+1}.0.0" if b == "major" else f"{ma}.{mi+1}.0" if b == "minor" else f"{ma}.{mi}.{pa+1}")
PY
)"
fi
echo "version: $OLD -> $NEW"

if [ "$NEW" != "$OLD" ]; then
  echo "$NEW" > VERSION
  python3 - "$NEW" "$MSG" <<'PY'
import json, re, sys, datetime
from pathlib import Path
new, msg = sys.argv[1], sys.argv[2]
p = Path(".claude-plugin/plugin.json"); d = json.loads(p.read_text()); d["version"] = new; p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
for s in Path("skills").glob("*/SKILL.md"):
    t = s.read_text(encoding="utf-8")
    t = re.sub(r"(?m)^version: .*$", f"version: {new}", t, count=1)
    s.write_text(t, encoding="utf-8")
c = Path("CHANGELOG.md"); t = c.read_text(encoding="utf-8")
entry = f"## [{new}] - {datetime.date.today().isoformat()}\n### Changed\n" + "".join(f"- {x.strip()}\n" for x in msg.split(";") if x.strip()) + "\n"
t = t.replace("\n## [", "\n" + entry + "## [", 1)
c.write_text(t, encoding="utf-8")
PY
fi

if command -v claude >/dev/null 2>&1; then claude plugin validate "$ROOT" || { echo "STOP: plugin validation failed"; exit 1; }; fi
python3 scripts/scan_private.py "$ROOT" >/dev/null || { echo "STOP: scan failed after bump"; exit 1; }

git add -A
git commit -q -m "release v$NEW: ${MSG}" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || echo "nothing to commit"
git tag -a "v$NEW" -m "v$NEW: ${MSG}" 2>/dev/null || echo "tag v$NEW already exists"
if [ "$PUSH" = "--push" ]; then git push origin HEAD --follow-tags; echo "pushed v$NEW"; else echo "committed and tagged v$NEW locally (no push)"; fi
