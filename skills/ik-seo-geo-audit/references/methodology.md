---
task-type: audit
applies-to-stages: [triage, plan]
status: shipped-default
sources: S1-S18 (see "Sources"); quotes are short excerpts from MIT / Apache-2.0 licensed skills, with attribution
---

# Prioritisation methodology for SEO/GEO audit findings

Used at two stages of the audit: **triage** (real issue vs noise; severity) and **plan** (what goes into the plan and in which order). A rule is here only when **at least three independent skills** state it; each rule carries a short verbatim quote per source. Where the sources disagree there is no rule — there is a **default** that the interview may change for a project (section "Defaults").

The audit chat must actually read this file (and the project's `owner-decisions.md`) and quote, verbatim and with headings, every rule it is going to use before starting triage or the plan. Where this file has a rule, "what usually works" is not allowed. Owner decisions of the project override the defaults, never the rules.

## Triage — decide by

**T1. Indexing and access blockers are the highest severity (Critical).** If a page that should be in search cannot be found or indexed, it is Critical, above any quality issue.
- S1: "No conflicting directives (e.g., canonical + noindex)"
- S8: "tags on pages that should be indexed"
- S11: "directly hurting rankings or preventing indexation"
- S12R: "Blocks discovery entirely, or states something false about the business"
- S18: "this is a critical issue." (a top page that is NOT_INDEXED / CRAWLED_CURRENTLY_NOT_INDEXED)

**T2. A finding is real only with a concrete URL, a concrete metric as evidence and a concrete fix.**
- S2: "provide the exact fix"
- S9: "Be specific — include file paths and line numbers"
- S11: "What to do (specific and concrete)"
- S18: "Every item must have a specific URL, a specific metric as evidence, and a specific fix — nothing generic."

**T3. "Not always an issue" — conditional cases are not defects unless the condition is proven on that page.**
- S4: "Not always bad, but reciprocal links strengthen topical clusters" (one-way links)
- S12R: "pointing at itself unless deliberately consolidating" (self-referencing canonical is fine)
- S17: "This isn't absolute" (the 3-click rule)
- S14R: "Stop when the content is at quality bar"
- S18: "skip the consolidation recommendation" (when several pages owning a SERP is a positive)

**T4. An estimate or a sample is never presented as a measured fact.**
- S12: "Do not estimate a visibility score."
- S13: "one run is an anecdote, not a measurement"
- S18: "note it's synthetic" (lab data instead of field data)

**T5. Never "fix" by inventing facts.** Anything proposed for a page or for markup must come from the site itself or from the owner.
- S3: "Never fabricate data — use what's actually on the page."
- S12: "Never write a claim the owner has not made."
- S14: "No Fabrication. Ever."
- S16: "Source of each data point clearly stated"

**T6. Title / description / OG defects are not Critical by themselves: Medium or a quick win.**
- S11: "best practice violation, moderate impact"
- S11: "Examples: fix title tags, add meta descriptions" (Quick Wins)
- S12R: "Fix titles and meta descriptions — medium impact, small effort"
- S18: "High-impression, low-CTR queries" (Quick Wins)

### Triage — never
- Accept a finding without a URL and evidence; use site-level evidence for a page-level claim (bottom-up).
- Mark Critical without an indexing/access block (T1).
- Report a T3 case as a defect without proof that the condition applies.
- Present an estimate as a measurement (T4) or invent numbers (T5).
- Report an owner decision from `owner-decisions.md` as a defect.

## Plan — decide by

**P1. Order by impact, not by ease.**
- S6: "Action Plan (Priority Order)"
- S9: "Prioritize findings by impact"
- S12: "Rank by impact, not by ease."
- S18: "ordered by expected click impact"

**P2. A short main list; the rest separately as "not now".** (How many items — default D4.)
- S12: "Give the owner the five that matter and put the rest in an appendix."
- S18: "Do not add a 6th item — triage ruthlessly."
- S11: "The top 3 priorities that will have the most impact"
- S14: "Top 5 Fixes (Highest Lift First)"

**P3. Separate quick wins from strategic investments; every step carries impact and effort.** (Effort scale — default D5.)
- S11: "Quick Wins (do this week):" and "Strategic Investments (plan for this quarter):"
- S14: "Expected lift: [N points] — Effort: [low/med/high]"
- S12R: "Score every finding on two axes. Rank by impact first."
- S18: "Quick Wins (highest impact, lowest effort)"

**P4. Money and traffic pages first.**
- S12R: "Money pages reachable in two clicks from the homepage"
- S13: "Keep the list to prompts that would change revenue."
- S14: "traffic potential × current GEO score gap"
- S18: "Prioritize: homepage first, then fill remaining slots with top pages by clicks"

**P5. An explicit "not now" list.**
- S8: "Opportunities (nice to have)"
- S12R: "Nine more findings in the appendix, none urgent."
- S18: "What to Ignore (For Now)"
- S9: "Opportunities (Nice to Have)"

**P6. Time horizons and a recheck date.**
- S11: "Strategic Investments (plan for this quarter):"
- S14: "Produce a 30/60/90 day GEO playbook for the site"
- S18: "actionable 30-day plan"
- S12: "Set a recheck date."

**P7. Every plan item: what to do, expected impact, effort, dependencies.**
- S11: "Expected impact (high, medium, low)" · "Dependencies (if any)"
- S12R: "High impact · 10 minutes"
- S18: "Effort: Low / Med / High"

### Plan — never
- Promise a timeline or a ranking (S12: "Do not promise a timeline or a ranking.").
- Propose manipulation: keyword stuffing, hidden text, fake reviews (S2: "Don't keyword-stuff — Google penalizes unnatural usage"; S12: "Do not use hidden text, cloaking, keyword stuffing, or fake reviews."; S14R: "Hidden text optimization"; S13: "Keyword stuffing").
- Invent facts, quotes or reviews for pages (T5).
- Put a step without "where exactly / expected result / how to verify".
- Count a change as "fixed" before the recheck; a successful command or HTTP 200 is not proof.

## Defaults (the interview may change them per project; record changes in `owner-decisions.md`)

| ID | Topic (sources disagree) | Default |
|---|---|---|
| D1 | Redirect chains: any chain (S1) vs 3+ hops (S5) | a defect from 3 hops; 2 hops = Low |
| D2 | Blocking AI crawlers: top issue (S12, S14) vs per-purpose decision (S13) vs owner's choice (S12R) | the owner decides; the audit only reports |
| D3 | Overall site score: yes (S1, S2, S8, S9, S14) vs "No overall score" (S12R) | no overall score |
| D4 | Main list length: 3 (S11), 3-5 (S18), 5 (S12, S14) | 5 |
| D5 | Effort scale: hours (S11) vs "one file, one field, under an hour" (S12R) | quick win = up to 2 hours |
| D6 | Severity levels: four (S11), three (S18), impact-only (S12R), errors/warnings (S15R) | Critical / High / Medium / Low (S11 definitions) |
| D7 | Orphan pages: every source checks them, none assigns a level | Medium for money/service pages in the sitemap, Low otherwise |
| D8 | Re-audit cadence: 30 days (S12), monthly (S13), 2 weeks (S14R), audit log (S18) | full audit quarterly; measurements and targeted checks monthly |
| D9 | Weight of schema markup: high impact, small effort (S12R) vs errors "must fix" (S15R) | validity errors = Medium (must fix); missing new types = Low/Medium |
| D10 | `llms.txt`: medium impact (S12) vs no confirmed signal (S13) vs optional (S14R) | missing/partial llms.txt = Low |
| D11 | Manual "Request indexing" | only for key pages, only after the owner's explicit yes |
| D12 | First check of results | 2 weeks for crawling; report monthly |

## Sources (upstream repositories; quotes are short excerpts with attribution)

| ID | Skill | Upstream | License |
|---|---|---|---|
| S1 | technical-seo | searchfit/searchfit-seo `skills/technical-seo` | MIT |
| S2 | on-page-seo | searchfit/searchfit-seo `skills/on-page-seo` | MIT |
| S3 | schema-markup | searchfit/searchfit-seo `skills/schema-markup` | MIT |
| S4 | internal-linking | searchfit/searchfit-seo `skills/internal-linking` | MIT |
| S5 | broken-links | searchfit/searchfit-seo `skills/broken-links` | MIT |
| S6 | ai-visibility | searchfit/searchfit-seo `skills/ai-visibility` | MIT |
| S8 | seo-audit | searchfit/searchfit-seo `skills/seo-audit` | MIT |
| S9 | seo-auditor (agent) | searchfit/searchfit-seo `agents/seo-auditor` | MIT |
| S11 | seo-audit | anthropics/knowledge-work-plugins `marketing/skills/seo-audit` | Apache-2.0 |
| S12 | seo-ai-visibility (+ `reference/audit_checklist.md` = S12R) | anthropics/knowledge-work-plugins `small-business/skills/seo-ai-visibility` | Apache-2.0 |
| S13 | ai-seo | coreyhaines31/marketingskills `skills/ai-seo` | MIT |
| S14 | geo-optimizer (+ `references/geo-techniques.md` = S14R) | nowork-studio/notfair-plugin `seo/geo-optimizer` | MIT |
| S15 | schema-markup-generator (+ `references/` = S15R) | nowork-studio/notfair-plugin `seo/schema-markup-generator` | MIT |
| S16 | meta-tags-optimizer | nowork-studio/notfair-plugin `seo/meta-tags-optimizer` | MIT |
| S17 | site-architecture | coreyhaines31/marketingskills `skills/site-architecture` | MIT |
| S18 | seo-analysis | nowork-studio/notfair-plugin `seo/seo-analysis` | MIT |

Quotes were checked against the upstream texts on 2026-10-05. When the version check reports that several of these sources changed substantially, rebuild this file (re-extract the quotes; keep a rule only with >= 3 agreeing sources).
