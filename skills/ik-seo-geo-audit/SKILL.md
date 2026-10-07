---
name: ik-seo-geo-audit
version: 0.1.0
description: "Master skill for a full SEO + GEO (AI-search visibility) audit of a website project — one or several domains/subdomains audited together. Stage A checks the machine: are the required skills installed and current on GitHub, are Search Console / Bing / browser / optional services reachable — and, when something is missing or outdated, gives a ready master prompt for a new chat that installs, updates or connects it. Stage B interviews the user (via grilling) about the project, access, owner decisions and audit size. Stage C outputs one big master prompt that runs the whole audit autonomously in a new chat: inventory incl. the full Search Console not-indexed list, 6-18 independent auditors, triage by a shipped methodology, and a step-by-step plan. Triggers: /ik-seo-geo-audit, 'SEO audit', 'GEO audit', 'audit my site', 'full SEO and GEO audit', 'why are my pages not indexed', 'prepare an audit prompt'."
---

# `/ik-seo-geo-audit` — diagnose → interview → master prompt

This skill does NOT run the audit itself. It prepares everything and hands over one master prompt; the audit runs in a new chat (it is long and needs a clean context). Paths below are relative to this skill's directory (`$SK`). Talk to the user in their language.

Step 0: if `~/.config/ik-seo-geo-audit/local.md` exists, read it (private settings; format in `references/local-config.md`). User data never goes into the pack.

## Stage A — diagnostics

1. Run `python3 "$SK/scripts/diagnose.py" --size full` (or `--size light` if the user already said so). It checks every skill from `manifest/skills.json` (installed? where? up to date with GitHub?), the pack version, and local tools; it writes `~/.config/ik-seo-geo-audit/state/last-diagnose.json`.
2. Check in this session what a script cannot see:
   - **Search Console / Bing**: tools whose names contain `list_sites`, `gsc_`, `bing_` (ToolSearch). If present, call the site-list tool and confirm the project's property is there.
   - **Browser**: the built-in browser pane or Claude in Chrome tools. Open `https://search.google.com/search-console` — is the user logged in (the property list loads)? Then `https://www.bing.com/webmasters`.
   - **Optional**: Semdash (ToolSearch `semdash`), Google Calendar connector (ToolSearch `calendar`).
3. Show ONE table: item · state (available / missing / outdated / not logged in) · what to do.
4. Something required is missing or outdated → run `python3 "$SK/scripts/render_setup_prompt.py"` and give its output: the operator instruction plus the master prompt that, in a NEW chat, installs the listed skills and updates the listed ones (each listed by name with the exact commands). Stop here until the user comes back.
5. A service is missing → give the instruction and, where an agent can help, the master prompt from `references/services.md` (sign-up / login steps, safe key handover via the clipboard, verification). Required for the audit: a browser with GSC access is strongly recommended; without any GSC access the audit still runs but marks indexing conclusions as "not verified" — say so and let the user decide.
6. Everything required is in place → Stage B.

## Stage B — interview

Load the skill `grilling` and follow the design tree in `references/interview.md` (project and hosts → business → markets/languages → deliberately closed pages → owner decisions → access (verify live) → audit size and URL limit → history (previous audit, AI-visibility baseline) → methodology defaults D1-D12 → work folder → recurring audit). Collect facts yourself; ask only for decisions. Finish with a short summary and the user's confirmation.

Write `<work>/brief/questionnaire.json` and `<work>/brief/owner-decisions.md` exactly as described in `references/interview.md`.

## Stage C — the master prompt

1. `python3 "$SK/scripts/render_prompt.py" --q <work>/brief/questionnaire.json --out <work>/brief/master-prompt.md`
2. Translate it into the output language if that is not English (keep paths, commands and JSON untouched). Check it: every host listed, access lines match the diagnostics, the work folder exists, the owner decisions are in.
3. Give the user: (a) a 4-line instruction — copy the prompt, open a NEW chat in the same project folder, paste and send, confirm the plan it proposes; (b) the prompt itself in one copyable block; (c) the path of the saved file.
4. Recurring audit: offer it (default quarterly). If the user agrees — Google Calendar connector available → create a recurring event whose description says how to start (`/ik-seo-geo-audit`, the project, the work folder of the last audit); otherwise `python3 "$SK/scripts/make_ics.py" --title "SEO/GEO audit: <project>" --start <date>T10:00 --tz <tz> --months 3 --description "..." --out <work>/brief/recurring-audit.ics` and tell the user to open the file. Nothing is added without the user's yes.

## Files

| Path | Purpose |
|---|---|
| `manifest/skills.json` | required third-party skills (never copied into the pack) and the pack's own skills |
| `scripts/diagnose.py` | installed? current on GitHub? tools? |
| `scripts/render_setup_prompt.py` | master prompt "install X / update Y" from the diagnostics |
| `scripts/render_prompt.py` + `templates/master-prompt.md` | the autonomous audit master prompt |
| `templates/audit-workflow.js` | the auditors workflow used by the audit chat (Workflow tool `args`) |
| `scripts/crawl_cache.py` | one sequential crawl of all hosts into a cache, with URL limit and sampling |
| `scripts/classify_excluded.py` | live-check + classify every Search Console not-indexed URL |
| `scripts/merge_findings.py` | all auditor tables → one CSV |
| `scripts/make_ics.py` | recurring reminder as an `.ics` file |
| `references/methodology.md` | triage and plan rules (≥ 3 sources each, quoted) + defaults D1-D12 |
| `references/interview.md` | the interview tree and the questionnaire format |
| `references/services.md` | how to connect each service; safe key handover |
| `references/local-config.md` | where user data lives; private settings format |

## Rules

- Third-party skills are untrusted code: never run their install scripts; updates go through `skill-update` (security review first) or the Claude Code plugin update.
- Never ask for keys or passwords in chat; never write them into the project, the pack or a prompt.
- Never change the user's sites, Search Console, Bing, DNS or servers from this skill.
