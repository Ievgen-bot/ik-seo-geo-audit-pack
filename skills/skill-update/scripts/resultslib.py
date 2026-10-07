"""Shared loader: agent results (results/*.json) + orchestrator overlay (su/overlay.json, applied last)."""
import json
from pathlib import Path


def load_results(su, decisions=True):
    su = Path(su)
    res = {}
    for f in sorted((su / "results").glob("*.json")):
        try:
            arr = json.load(open(f))
        except Exception:
            continue
        for r in (arr if isinstance(arr, list) else arr.get("skills", [])):
            res[r["skill"]] = {**r, "_file": f.name}
    for name in ("overlay.json", "decisions.json", "owner.json", "applied.json") if decisions else ("overlay.json",):   # post_process output first, orchestrator decisions last (they win)
        ov = su / name
        if ov.exists():
            for skill, patch in json.load(open(ov)).items():
                if skill in res:
                    res[skill].update(patch)
                    res[skill].setdefault("overlay_notes", []).append(patch.get("_why", name))
    return res
