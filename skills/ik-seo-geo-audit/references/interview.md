# Interview (stage B) — what to ask and what to produce

Run it with the skill `grilling`: rounds, one numbered question per open decision, your recommended answer under each, wait for the answers, recompute the frontier. Facts you can find yourself (sitemaps, robots.txt, GSC property list, diagnostics) are YOUR job — never ask the user for them. Ask in the user's language.

## Design tree (ask a branch only when its prerequisites are answered)

1. **Project and hosts.** Which domains and subdomains belong to this project (one business = one project; several hosts are audited together and cross-host problems are part of the audit)? Any host to exclude? Different, unrelated businesses → separate projects and separate prompts.
   - Facts to collect yourself first: each host's robots.txt, sitemaps, redirects between hosts (`curl -sI`), whether `www`/apex/`http` resolve.
2. **Business.** What it sells, to whom, where; which pages make money (services, products, lead forms); is it a personal brand?
3. **Markets and languages.** Countries/regions, the languages of paying customers, which language versions exist; the language of the deliverables.
4. **What is deliberately closed.** Pages hidden on purpose and how (noindex, absent from sitemap, robots, login). These are owner decisions, never findings.
5. **Owner decisions and red lines.** Things the audit must not recommend (e.g. "the tag manager always loads", "no localized homepages", "no prices on the site"). Each becomes a line in `owner-decisions.md`.
6. **Data access** (verify each answer live — do not trust "yes, I have it"):
   - Search Console: MCP tools present? else the browser — ask the user to log in to the Google account that owns the property, then open the property list yourself; else none.
   - Bing Webmaster: same order. Note whether apex and `www` are separate properties.
   - Browser: built-in browser pane or the Claude in Chrome extension; if neither works → give the extension install steps (skill `ik-seo-webmaster`, Path B) and wait.
   - TypeSafe key for calibrated triage (optional); Semdash or other paid SEO data (optional, with a budget: ask the credit ceiling).
7. **Audit size.** Full (17-18 auditors, default) or light (6: technical, on-page, schema, internal links, Search Console/Bing, GEO). Crawl URL limit (default 300 for the whole project; sampled above it).
8. **History.** A previous audit to mark regressions against (path)? An existing AI-visibility baseline (path)? Then the plan schedules a recheck instead of a baseline.
9. **Methodology defaults.** Show the defaults D1-D12 from `references/methodology.md` in one compact table; ask only which ones to change for this project.
10. **Where results go.** Work folder (default `<current project>/seo-audit/<project-slug>/<YYYY-MM-DD>/`).
11. **Recurring audit.** Offer a recurring full audit (default quarterly). If the user agrees: Google Calendar connector present → create the event; otherwise produce an `.ics` with `scripts/make_ics.py`.

Stop when the frontier is empty and the user confirms the summary.

## What the interview must produce

`<work>/brief/questionnaire.json`:
```json
{
  "project_name": "Example Studio",
  "hosts": ["https://example.com", "https://shop.example.com"],
  "business": "what it sells, to whom, where (1-3 lines)",
  "money_pages": "/services/*, /pricing, /contact",
  "markets": "Ukraine, EU", "languages": "uk, en", "output_language": "Ukrainian",
  "owner_decisions": ["Pages hidden by noindex + absent from the sitemap are deliberately closed", "..."],
  "never_recommend": ["deferring the tag manager"],
  "gsc": "mcp | browser | none", "bing": "browser UI, www property only",
  "browser": "built-in browser pane",
  "typesafe": true, "semdash": false, "semdash_budget": "",
  "size": "full", "url_limit": 300, "main_list": 5,
  "previous_audit": null, "measurement_baseline": null,
  "work_dir": "/abs/path/seo-audit/example-studio/2026-10-07"
}
```

`<work>/brief/owner-decisions.md`: one bullet per decision or red line, plus the methodology defaults the user changed ("D4: main list = 3"), each with the date of the interview.

Then run `scripts/render_prompt.py --q <work>/brief/questionnaire.json --out <work>/brief/master-prompt.md`, translate the result into the output language if it is not English (keep paths, commands and JSON as they are), and give it to the user.
