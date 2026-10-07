export const meta = {
  name: 'ik-seo-geo-audit-auditors',
  description: 'Independent SEO/GEO auditors (one skill or data source each) over a cached multi-host project; each writes its own report',
  phases: [
    { title: 'Audit', detail: 'auditors in parallel, each loads its own skill' },
    { title: 'Collect', detail: 'save reports returned as text' },
  ],
}

// args = { work: "<abs path of the audit folder>", hosts: ["https://example.com", ...], project: "<1-3 lines: business, markets, languages>",
//          size: "full" | "light", gsc: "mcp" | "files" | "none", semdash: true|false,
//          decisions: "<abs path of owner-decisions.md>", geo_sources: ["<abs path>", ...] (optional private GEO method files) }
const W = args.work
const HOSTS = args.hosts.join(', ')

const COMMON = `
You are ONE independent auditor in a multi-agent SEO + GEO audit of this project: ${HOSTS}.
Project: ${args.project}
You audit FROM SCRATCH using ONLY your assigned skill / data source. You do not know what other auditors found and must not look.

DATA YOU MAY USE
- Pre-crawled cache: ${W}/cache/_index.json (fields url, host, status, secs, bytes, file, headers, in_sitemap); each file is the raw response body; coverage and sampling: ${W}/cache/_sample.md. Prefer the cache over live requests.
- Live requests only when the cache cannot answer: at most 15 per agent, strictly sequential, >=1 s apart, 60 s timeout. Never run a crawler or parallel fetches.
- Search Console / Bing exports made at stage 0 (if any): ${W}/00-inventory.md and ${W}/_data/.
- Owner decisions — NOT defects, never report them as problems: ${args.decisions}
- Cross-host view: always check problems BETWEEN the hosts too (duplicate pages on two hosts, canonical/redirect conflicts, www/apex/http variants, one entity described differently on different hosts).

HARD RULES
- READ-ONLY. Do not change any site, repository, Search Console, Bing, sitemap; no indexing requests, no form submissions. No secrets: never read .env, tokens, key files.
- Do NOT read other files in ${W}/audits/ (only write yours) and do not read any earlier audit of this project.
- Evidence rule (bottom-up): every finding needs a concrete URL and verbatim evidence (quoted HTML / header / API field / count). A site-level observation does not prove a page-level claim. No evidence -> do not list it. Never invent numbers.
- Stay inside your skill's scope; quality over quantity.

OUTPUT
Write your report with the Write tool to the exact path below (Markdown, in the language of the project brief; quotes/code verbatim). Format: a title, a 5-10 line summary, then ONE table:
| URL | issue | evidence (quote / header / API field) | severity guess (critical/high/medium/low) | skill rule |
'skill rule' = the rule/check name from your skill. Site-wide findings: URL = the host root, 2-3 sample URLs in evidence. Then 'Checked and OK' and 'Could not check (why)'.
Return the structured result. status: ok | auth_failed | unavailable | sandbox_blocked | error. If your skill/tool could not be loaded, say exactly why and still write a report stating that (never substitute another skill silently).`

const SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['ok', 'auth_failed', 'unavailable', 'sandbox_blocked', 'error'] },
    status_reason: { type: 'string' },
    report_path: { type: 'string' },
    findings_count: { type: 'number' },
    top_findings: { type: 'array', items: { type: 'string' } },
    report_markdown: { type: 'string' },
  },
  required: ['status', 'status_reason', 'report_path', 'findings_count'],
}

const GSC = args.gsc === 'mcp'
  ? `Use the Search Console / Bing MCP tools (find them with ToolSearch: 'search console', 'bing'; call the site-list tool first). READ-ONLY tools only. Inspect every URL of class 'target page' in ${W}/_data/gsc-excluded-classified.tsv one at a time (current coverage state, last crawl, Google canonical vs user canonical); report which excluded pages are STILL excluded now. Also: top queries/pages, CTR vs position gaps, 28/90-day trend, Bing crawl/index stats.`
  : `No GSC/Bing API in this run. Use the exports from stage 0 (${W}/00-inventory.md, ${W}/_data/) as your data source and report indexing problems from them; state clearly what could not be verified without live URL inspection.`

const ALL = [
  { n: '01', slug: 'technical-seo', skill: 'technical-seo', light: true, how: `Load the skill 'technical-seo' (searchfit-seo) and apply it: indexing, robots, canonical, hreflang, redirects, status codes, headers, sitemaps — per host and across hosts.` },
  { n: '02', slug: 'on-page-seo', skill: 'on-page-seo', light: true, how: `Load the skill 'on-page-seo' (searchfit-seo): titles, descriptions, H1-H3, content, images/alt; sample at least 25 representative URLs across hosts and languages.` },
  { n: '03', slug: 'schema-markup', skill: 'schema-markup', light: true, how: `Load the skill 'schema-markup' (searchfit-seo): JSON-LD on all page types, validity, @id graph consistency across hosts.` },
  { n: '04', slug: 'internal-linking', skill: 'internal-linking', light: true, how: `Load the skill 'internal-linking' (searchfit-seo): build the link graph from the cache, orphan pages, weak hubs, anchors, depth; links between hosts.` },
  { n: '05', slug: 'broken-links', how: `Load the skill 'broken-links' (searchfit-seo): internal links against the cache, external links with at most 15 sequential live checks (prioritise prominent ones).` },
  { n: '06', slug: 'ai-visibility', how: `Load the skill 'ai-visibility' (searchfit-seo) and apply it to the site as it is (structure, citability, AI-crawler access, entity clarity). Do NOT measure live AI answers.` },
  { n: '07', slug: 'keyword-clustering', how: `Load the skill 'keyword-clustering' (searchfit-seo): derive the topic set from titles/H1/content, cluster it, find cannibalisation and missing clusters. ${args.gsc === 'mcp' ? 'You may use the GSC MCP read-only (top queries) to ground clusters.' : ''}` },
  { n: '08', slug: 'seo-auditor-agent', agentType: 'searchfit-seo:seo-auditor', how: `You are the end-to-end SEO auditor: cover technical, on-page, content, structure and GEO basics of the whole project.` },
  { n: '09', slug: 'competitor-analyzer-agent', agentType: 'searchfit-seo:competitor-analyzer', noWrite: true, how: `Identify (via web search) the real organic and AI-answer competitors of this business for its markets and compare their SEO/content/schema/citability with the project. If you cannot write files, put the full report into report_markdown.` },
  { n: '10', slug: 'marketing-seo-audit', how: `Load the skill 'marketing:seo-audit' and apply it to the whole project.` },
  { n: '11', slug: 'small-business-seo-ai-visibility', how: `Load the skill 'small-business:seo-ai-visibility' and apply it to the whole project (no live AI measurement).` },
  { n: '12', slug: 'ai-seo-geo-optimizer', light: true, how: `Load BOTH skills 'ai-seo' and 'geo-optimizer' and apply them together: AI/LLM citability, answer structure, llms.txt / agent-readiness, entity signals, AI-crawler access. Do NOT measure live AI answers.` },
  { n: '13', slug: 'schema-generator-meta-optimizer', how: `Load BOTH skills 'schema-markup-generator' and 'meta-tags-optimizer': meta tags (title/description/OG/Twitter/canonical/hreflang/robots) and JSON-LD per page type; give the corrected value in evidence.` },
  { n: '14', slug: 'site-architecture', how: `Load the skill 'site-architecture': URL structure, hierarchy, depth, navigation, language versions, how the hosts fit together, sitemap vs menu consistency.` },
  { n: '15', slug: 'seo-analysis', how: `Load the skill 'seo-analysis' and apply it (if its scripts need cloud credentials that are absent, use the cache and the stage-0 data instead and say so).` },
  { n: '16', slug: 'search-console-bing', light: true, how: `Load the skill 'ik-seo-webmaster'. ${GSC}` },
  { n: '17', slug: 'semdash', optional: 'semdash', how: `Use ONLY the Semdash MCP tools (ToolSearch 'semdash'). Be economical: at most ~25 paid calls, <=50 rows each, one call per question. Ranked keywords per market, pages by traffic, backlinks and referring domains (quality, spam), competitor domains and keyword gap vs the 2 closest real competitors, a SERP check of 3-5 core queries. Report what is in the data; mention the number of paid calls in status_reason.` },
  { n: '18', slug: 'ai-visibility-axes', how: `Assess the project's readiness for AI-assistant recommendations along the three axes described in the skill 'ik-ai-visibility-baseline' (load it): ENTITY (one unambiguous identity: a canonical who/what/for whom/where/proof paragraph, consistent facts and names across all hosts and profiles, linked related entities), BREADTH (independent mentions on other sites, visible from the cache and web search), DEPTH (own primary-source content: hub pages, original data, named methods). ${(args.geo_sources || []).length ? 'Also read these method files ONE AT A TIME and apply them: ' + args.geo_sources.join(', ') + '.' : ''} Report gaps with page evidence. Do NOT run the live AI measurement itself.` },
]

const A = ALL.filter(a => (args.size === 'light' ? a.light : true) && (!a.optional || args[a.optional]))
log(`auditors: ${A.map(a => a.n).join(', ')}${args.size === 'light' ? ' (light)' : ''}`)

async function runOne(a) {
  const path = `${W}/audits/${a.n}-${a.slug}.md`
  const prompt = `${COMMON}\n\nYOUR ASSIGNMENT (#${a.n}): ${a.how}\nREPORT FILE (write exactly here): ${path}\n${a.noWrite ? 'If you cannot write files, put the whole report in report_markdown.' : ''}`
  let r = null
  if (a.agentType) {
    try { r = await agent(prompt, { label: `${a.n} ${a.slug}`, phase: 'Audit', schema: SCHEMA, agentType: a.agentType }) } catch (e) { r = null }
    if (!r) log(`#${a.n}: agent type ${a.agentType} unavailable -> default agent`)
  }
  if (!r) r = await agent(prompt, { label: `${a.n} ${a.slug}`, phase: 'Audit', schema: SCHEMA })
  if (!r) return { n: a.n, slug: a.slug, status: 'error', status_reason: 'agent returned null', report_path: path, findings_count: 0 }
  return { n: a.n, slug: a.slug, path, ...r }
}

const results = await pipeline(A, a => runOne(a), async (r, a) => {
  if (r && r.report_markdown && r.report_markdown.length > 200) {
    await agent(`Write the following text EXACTLY and in full to the file ${r.path} using the Write tool, then reply 'saved'.\n\n${r.report_markdown}`, { label: `save ${a.n}`, phase: 'Collect' })
  }
  const { report_markdown, ...rest } = r
  return rest
})
log(`finished: ${results.filter(Boolean).length}/${A.length}`)
return results
