#!/usr/bin/env python3
"""Directory hashing and diffing for skill trees (read-only).

  tree_tool.py hash DIR [--out FILE]                       per-file sha256/size/mode + tree_id (same formula as the manifest)
  tree_tool.py diff A B [--ignore-eol] [--ignore-mode]     compare two trees (junk excluded); exit 0 always
  tree_tool.py gitblob FILE_OR_DIR                         git blob sha1 for each file (compare with `git ls-tree -r`)
Junk excluded everywhere: .git, node_modules, __pycache__, .DS_Store, ._*, *.pyc
"""
import hashlib, json, os, sys
from pathlib import Path

JUNK_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


def walk(root: Path):
    """Yield (relpath, Path) in the same order as the manifest builder (sorted dirs/files per directory)."""
    for p, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in JUNK_DIRS)
        for f in sorted(files):
            if f == ".DS_Store" or f.startswith("._") or f.endswith(".pyc"):
                continue
            fp = Path(p) / f
            yield str(fp.relative_to(root)), fp


def tree_hash(root: Path):
    files, h = {}, hashlib.sha256()
    for rel, fp in walk(root):
        try:
            data = fp.read_bytes()
            st = fp.lstat()
        except OSError:
            continue  # dangling symlink / unreadable: skipped (same rule as build_manifest.tree_id)
        sha = hashlib.sha256(data).hexdigest()
        files[rel] = {"sha256": sha, "size": len(data), "mode": "symlink" if fp.is_symlink() else format(st.st_mode & 0o777, "o")}
        h.update(rel.encode()); h.update(bytes.fromhex(sha))
    return {"tree_id": h.hexdigest()[:16], "file_count": len(files), "files": files}


def gitblob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def norm_eol(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "hash":
        t = tree_hash(Path(sys.argv[2]))
        if "--out" in sys.argv:
            Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(t, indent=1))
        print(json.dumps({"tree_id": t["tree_id"], "file_count": t["file_count"]}))
    elif cmd == "gitblob":
        p = Path(sys.argv[2])
        if p.is_file():
            print(gitblob(p.read_bytes()), p.name)
        else:
            for rel, fp in walk(p):
                print(gitblob(fp.read_bytes()), rel)
    elif cmd == "diff":
        a, b = Path(sys.argv[2]), Path(sys.argv[3])
        ie, im = "--ignore-eol" in sys.argv, "--ignore-mode" in sys.argv
        fa, fb = {r: p for r, p in walk(a)}, {r: p for r, p in walk(b)}
        only_a, only_b = sorted(set(fa) - set(fb)), sorted(set(fb) - set(fa))
        changed, mode_only, same = [], [], 0
        for r in sorted(set(fa) & set(fb)):
            da, db = fa[r].read_bytes(), fb[r].read_bytes()
            if ie:
                da, db = norm_eol(da), norm_eol(db)
            if da != db:
                changed.append({"file": r, "size_a": len(da), "size_b": len(db)})
            elif not im and (fa[r].stat().st_mode & 0o111) != (fb[r].stat().st_mode & 0o111):
                mode_only.append(r)
            else:
                same += 1
        out = {"identical_files": same, "only_in_A": only_a, "only_in_B": only_b, "changed": changed, "mode_only": mode_only,
               "identical": not (only_a or only_b or changed or mode_only)}
        print(json.dumps(out, ensure_ascii=False, indent=1) if len(only_a) + len(only_b) + len(changed) < 60 else
              json.dumps({**out, "only_in_A": only_a[:30] + ["..."], "only_in_B": only_b[:30] + ["..."], "changed": changed[:30]}, ensure_ascii=False, indent=1))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
