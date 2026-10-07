---
name: ik-seo-webmaster
version: 0.1.0
description: "Live Google Search Console and Bing Webmaster Tools data for a site: indexing (excluded pages by reason, URL inspection), sitemaps, top queries and pages, clicks/impressions/CTR/position, Bing crawl and index stats. Works through any connected MCP server that exposes GSC/Bing tools, otherwise through the browser (built-in browser pane or the Claude in Chrome extension) on the user's logged-in accounts. Read-only by default; submissions only after explicit approval. Triggers: /ik-seo-webmaster, 'Search Console', 'GSC', 'Bing Webmaster', 'which pages are not indexed', 'excluded pages', 'top queries', 'indexing status', 'URL inspection'."
---

# `/ik-seo-webmaster` — Search Console + Bing for one site

Step 0: if `~/.config/ik-seo-webmaster/local.md` exists, read it first. It holds the user's own setup (their MCP server, accounts, known failures) and overrides the generic rules below.

Pick the first path that works and say which one you use.

## Path A — an MCP server with GSC/Bing tools

Look for tools whose names contain `list_sites`, `gsc_` or `bing_` (load deferred tools via ToolSearch with the query `search console` / `bing`).

1. Always start with the site list tool. Never guess a property string. Prefer the domain property `sc-domain:<domain>` (covers all protocols and subdomains); otherwise the URL-prefix property with `https://`.
2. Several matches or none → ask the user ONE question which property to use. Bing properties are listed separately.
3. Typical reads: top queries/pages for N days, totals, search analytics with dimensions, URL inspection (quota ~2000/day/site), sitemaps with errors, Bing crawl stats/issues/URL info.
4. Data caveats: GSC data lags 2-3 days; row sums by query are lower than totals (anonymized queries); Bing does not expose AI/Copilot performance through its API — say so, never invent numbers.
5. Any write (sitemap submission, URL submission, indexing request) only as: prepare → show the exact list → explicit "yes" for that list → confirm.

## Path B — the browser (no MCP)

Use the built-in browser pane (Claude desktop app) or the Claude in Chrome extension. The user must be logged in to the Google account that owns the GSC property and to Bing Webmaster Tools. If not logged in, ask them to log in in that browser, then check again. Never type passwords yourself.

Install the extension if neither browser is available: Chrome Web Store → "Claude" by Anthropic (Claude in Chrome) → sign in → allow it for Claude Code. Then retry.

### GSC — Page indexing report (full list of not-indexed URLs by reason)
The API does not return this list; read it from the UI.
1. Open `https://search.google.com/search-console/index?resource_id=<url-encoded property>` (e.g. `sc-domain%3Aexample.com`). Read "Not indexed N / Indexed M" and the reasons table (reason, source, pages).
2. Note the date the chart ends: the report can lag weeks behind reality. Current state of a URL = URL Inspection, not this report.
3. For each reason: click its row → in the drilldown find the listbox "Rows per page" and select 100 (or 500) → read the table. Extraction snippet (run in the page):
   ```js
   const lines=document.body.innerText.split('\n').map(s=>s.trim()).filter(Boolean);
   const out=[]; for(let i=0;i<lines.length;i++){ if(/^https?:\/\//.test(lines[i]) && !/sitemap\.xml$/.test(lines[i])) out.push(lines[i]+' | '+((/^https?:/.test(lines[i+1]||'')||!lines[i+1])?'':lines[i+1])); }
   JSON.stringify({foot:lines.filter(l=>/^1–\d+ /.test(l)), out})
   ```
   The footer (`1–62 of 62`) must equal the count on the overview; if not, raise rows per page. The UI table is capped at 1000 rows per reason.
4. Do not use the "Export" button unless the user allowed a file download.
5. `history.back()` inside a script can leave the page — prefer navigating to the overview URL again before the next reason.

### GSC — URL Inspection, sitemaps, performance
- URL Inspection: the search bar at the top of GSC, one URL at a time; record coverage state, last crawl date, Google-selected canonical vs user canonical, robots/indexing state.
- Sitemaps: Indexing → Sitemaps; list every submitted sitemap with status and discovered URLs (dead or duplicate-host sitemaps are a finding).
- Performance: Search results; read the queries and pages tables for 28 / 90 days.
- Never click "Request indexing", "Submit", "Remove" or "Validate fix" without the user's explicit "yes" for that exact action.

### Bing Webmaster Tools
Open `https://www.bing.com/webmasters`, choose the site (note whether apex and `www` are separate properties), read Search Performance, Site Explorer / URL Inspection, Sitemaps and crawl information. Same write rule as GSC.

## Path C — no access

Say plainly that GSC/Bing data is unavailable and what is lost (excluded-URL list, real indexing state, queries). Continue with public data only (live crawl, sitemap, robots.txt) and mark every conclusion that would need GSC as "not verified".

## Out of scope

Deleting properties, sitemaps or users; changing settings; replying to reviews. Recurring reports and full audits only when the user explicitly asks (the full audit is `ik-seo-geo-audit`).
