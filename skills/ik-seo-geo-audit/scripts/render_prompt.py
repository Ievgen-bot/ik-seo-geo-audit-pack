#!/usr/bin/env python3
"""render_prompt.py — build the big master prompt for the autonomous audit chat from the interview answers
(questionnaire.json), the last diagnostics and the optional private settings (~/.config/ik-seo-geo-audit/local.md).

usage: render_prompt.py --q <work>/brief/questionnaire.json [--out <work>/brief/master-prompt.md]
questionnaire.json keys: see references/interview.md ("What the interview must produce").
"""
import argparse, json, re
from pathlib import Path

HERE = Path(__file__).resolve()
SKILL = HERE.parent.parent
CFG = Path.home() / ".config" / "ik-seo-geo-audit"

def local_settings():
    f = CFG / "local.md"
    if not f.exists():
        return {}
    m = re.search(r"```json\s*(\{.*?\})\s*```", f.read_text(encoding="utf-8"), re.S)
    return json.loads(m.group(1)) if m else {}

ap = argparse.ArgumentParser(); ap.add_argument("--q", required=True); ap.add_argument("--out")
a = ap.parse_args()
q = json.load(open(a.q, encoding="utf-8"))
diag = {}
try:
    diag = json.load(open(CFG / "state" / "last-diagnose.json"))
except Exception:
    pass
loc = local_settings()

size = q.get("size", "full")
semdash = bool(q.get("semdash"))
auditors = 6 if size == "light" else (18 if semdash else 17)
work = q["work_dir"].rstrip("/")
gsc = q.get("gsc", "none")  # mcp | browser | none
typesafe = q.get("typesafe", diag.get("tools", {}).get("typesafe_key") == "present")
prev = q.get("previous_audit")
decisions_path = f"{work}/brief/owner-decisions.md"
wf_args = {"work": work, "hosts": q["hosts"], "project": q["business"][:300], "size": size,
           "gsc": "mcp" if gsc == "mcp" else ("files" if gsc == "browser" else "none"),
           "semdash": semdash, "decisions": decisions_path, "geo_sources": loc.get("geo_sources", [])}
V = {
    "output_language": q.get("output_language", "English"),
    "project_name": q["project_name"],
    "hosts_list": "\n".join(f"- {h}" for h in q["hosts"]),
    "business": q["business"], "money_pages": q.get("money_pages", "not specified"),
    "markets": q.get("markets", "not specified"), "languages": q.get("languages", "not specified"),
    "work_dir": work, "auditor_count": str(auditors), "size": size,
    "regressions_note": f"; regressions against the previous audit ({prev}) are marked" if prev else "",
    "regressions_done": "; regressions against the previous audit are marked" if prev else "",
    "regressions_step": f" (+ mark regressions: read `{prev}` ONLY at this stage)" if prev else "",
    "owner_decisions": "\n".join(f"- {x}" for x in q.get("owner_decisions", [])) or "- none recorded",
    "never_recommend": "; ".join(q.get("never_recommend", [])) or "nothing specified",
    "diagnosed_at": diag.get("checked_at", "not run"),
    "gsc": {"mcp": "MCP tools available", "browser": "browser UI (logged in)", "none": "NOT available"}[gsc],
    "bing": q.get("bing", "browser UI" if gsc != "none" else "NOT available"),
    "browser": q.get("browser", "built-in browser pane / Claude in Chrome"),
    "typesafe": "available (calibrate before use)" if typesafe else "not available -> sub-agent triage labelled 'uncalibrated'",
    "semdash": f"allowed, budget: {q.get('semdash_budget', 'show the estimate first')}" if semdash else "not used",
    "url_limit": str(q.get("url_limit", 300)),
    "measurement_note": (f"; a baseline already exists at {q['measurement_baseline']}: plan a recheck with `ik-ai-visibility-recheck`" if q.get("measurement_baseline") else ""),
    "methodology_path": str(SKILL / "references" / "methodology.md"),
    "decisions_path": decisions_path,
    "extra_methodology": ("\nAlso read these additional method files of the owner (private, local) and apply them with the same gate: " + ", ".join(loc["extra_methodology"])) if loc.get("extra_methodology") else "",
    "pack_scripts": str(SKILL / "scripts"),
    "dashboard_note": "; also mirror every stage to the local `orq` dashboard (orq run start / task add / task update / run finish)" if loc.get("dashboard") == "orq" else "",
    "gsc_method": {"mcp": "MCP tools + the browser for the per-reason URL lists, which the API does not return", "browser": "the browser: Indexing report, each reason, rows per page 100/500 (see skill ik-seo-webmaster, Path B)", "none": "not available: say so in the inventory and continue with public data"}[gsc],
    "workflow_template": str(SKILL / "templates" / "audit-workflow.js"),
    "workflow_args": json.dumps(wf_args, ensure_ascii=False),
    "triage_method": ("TypeSafe: copy `ik-typesafe/questions/seo-finding-triage.json` into the folder, fill context.site and context.owner_decisions_not_issues, label 20-30 examples strictly by the methodology (add deliberately broken rows for rare classes), `jev calibrate` >= 0.90 on every question, then run all rows (dry-run and request ceiling first)"
                      if typesafe else "a triage sub-agent applying the same rubric (questions/seo-finding-triage.json) to every row; label the result 'uncalibrated'"),
    "main_list": str(q.get("main_list", 5)),
    "handoff_note": f" (also copy it to {loc['handoff_outbox']})" if loc.get("handoff_outbox") else "",
}
tpl = (SKILL / "templates" / "master-prompt.md").read_text(encoding="utf-8")
out = re.sub(r"\{\{(\w+)\}\}", lambda m: V.get(m.group(1), m.group(0)), tpl)
left = re.findall(r"\{\{\w+\}\}", out)
if left:
    raise SystemExit(f"unfilled placeholders: {left}")
if a.out:
    Path(a.out).write_text(out, encoding="utf-8"); print("written", a.out, len(out), "chars")
else:
    print(out)
