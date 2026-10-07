This is a new chat. Run a full autonomous SEO + GEO audit of one project. Write every message to me in {{output_language}}.
Name this chat: "SEO/GEO audit: {{project_name}}".

TASK
Audit the project "{{project_name}}" from scratch with independent auditors (one skill or data source each), triage all findings by the methodology, and deliver a step-by-step plan. Hosts in scope (one project, data combined, cross-host problems included):
{{hosts_list}}
Business: {{business}}
Money / key pages: {{money_pages}}
Markets and languages: {{markets}} · {{languages}}
This task ends with the plan. NO changes to any site, Search Console, Bing, server or DNS. Fixes are a separate chat.

EXPECTED RESULT — folder {{work_dir}}
- `status.md` — stages, progress, blockers (update it at every stage change).
- `00-inventory.md` — every URL: live sitemaps per host, the FULL list of URLs that Search Console reports as not indexed (by reason, each classified), Bing state; counts must match the GSC UI.
- `audits/NN-<skill>.md` — one report per auditor ({{auditor_count}} auditors, size: {{size}}).
- `03-findings.csv` + `03-summary.md` — deduplicated, validated, severity-scored findings{{regressions_note}}.
- `PLAN.md` — the main deliverable.
- `handoff.md` — decisions, results, what did not work, next step (so the next chat does not start from zero).

OWNER DECISIONS (never report them as defects; they override defaults of the methodology)
{{owner_decisions}}
Never recommend: {{never_recommend}}

ACCESS (from the diagnostics of {{diagnosed_at}})
- Search Console: {{gsc}} · Bing: {{bing}}
- Browser for GSC/Bing UI: {{browser}}
- TypeSafe (jev) for triage: {{typesafe}}
- Semdash (paid credits): {{semdash}}
- URL limit for the crawl: {{url_limit}} (above it, hosts are sampled: all non-blog pages first; the sample is reported).

DO NOT
- Do not change any site, do not commit, push or deploy.
- Without my separate "yes": Search Console "Request indexing", submitting or removing sitemaps, URL removals, IndexNow, any Bing change, server/DNS changes, paid calls beyond the budget shown to me first.
- Do not read secrets (.env, key/token files); never put keys into prompts.
- Do not let auditors see each other's reports or any earlier audit.
- Do not accept a finding without a URL and evidence; site-level evidence does not prove a page-level claim (bottom-up).
- Do not start triage or the plan without an actual read of the methodology file and verbatim quotes of the rules you will use.

DONE WHEN
- All auditor reports exist; any failed auditor is named with the reason (auth_failed / unavailable / sandbox_blocked / error).
- Every URL of the FULL "not indexed" export is classified (target page / intentionally closed / legacy CMS / duplicate host or URL / other) with a reason and a proposed action; counts match the GSC UI.
- `03-findings.csv` has source auditor, URL, evidence, verdict, severity{{regressions_done}}; if TypeSafe is used, calibration >= 90 % on 20-30 labelled examples is documented, otherwise the triage is labelled "uncalibrated".
- `PLAN.md`: every step = what to do · exactly where (file / route / host / GSC / Bing) · expected result · how to verify · the methodology rule it follows. Sections: not-indexed pages · technical SEO (per host + between hosts) · on-page / content · schema / entity · GEO (entity / breadth / depth) · AI-visibility measurement as a separate step (`ik-ai-visibility-baseline`{{measurement_note}}) · ongoing optimisation process (what, how often, who / which tool) · what NOT to do.
- A successful command or HTTP 200 is not proof: verify where I would see the result.

METHODOLOGY — hard gate
Copy `{{methodology_path}}` into the work folder together with `owner-decisions.md` ({{decisions_path}}). Before triage and before the plan: read both files with a tool and quote, verbatim and with headings, every "decide by" rule you will use. Where the file has a rule, your own judgement is not allowed. Gap or conflict → stop and ask me.{{extra_methodology}}

SKILLS — load before the first change
`ik-seo-geo-audit` (scripts and templates), `ik-seo-webmaster` (GSC/Bing), `ik-typesafe` (if a key exists), and each auditor's own skill. Scripts (run from the pack): `{{pack_scripts}}/crawl_cache.py`, `classify_excluded.py`, `merge_findings.py`.

ROUTE
0. Prep: create the folder and `status.md`{{dashboard_note}}. Inventory: live sitemaps of every host; the full not-indexed list per reason from GSC ({{gsc_method}}); classify it with `classify_excluded.py`; Bing state; then cache every page once with `crawl_cache.py --limit {{url_limit}}` (one --host per host) → `00-inventory.md` → counts match the GSC UI.
1. Methodology + owner decisions copied and read (see the gate).
2. Auditors — I explicitly opt in: use a workflow (multi-agent orchestration) with {{auditor_count}} auditors, above the default size guideline. Run the Workflow tool with the script `{{workflow_template}}` and args:
   {{workflow_args}}
   If the Workflow tool is unavailable, run the same auditors as background Agent calls in batches of 6. Every auditor writes `audits/NN-*.md` in the common table format.
3. Triage: `merge_findings.py` → one CSV of all findings → group duplicates into canonical issues (a sub-agent) → {{triage_method}} → your final verdict per issue with the reason when you differ from the automatic one → `03-findings.csv`, `03-summary.md`{{regressions_step}}.
4. Plan: `PLAN.md` by the methodology (main list of {{main_list}} items + "not now" appendix; time horizons; recheck dates).
5. Handoff: `handoff.md`{{handoff_note}}; update `status.md` to the real final state.

BEFORE STARTING, write briefly (up to 15 lines) and wait for my confirmation: the goal in one sentence; scope and what is out; what you read; the stage plan; the acceptance checklist with how you will verify each item; risks and actions that need my separate "yes"; one clarifying question if anything is ambiguous (or say there is none).

DURING WORK
- The simplest solution that is good enough; do not widen the scope.
- Do not ask permission for the next step of the agreed route when the previous one finished clean; stop at blockers and at the methodology gate.
- Status updates: done / blocking / questions, 1-3 lines each.

FINAL
Go through the acceptance checklist and show the actual verification. Status: DONE / PARTIAL / NOT DONE / BLOCKED. Then: what was done · what works now · what is left.
