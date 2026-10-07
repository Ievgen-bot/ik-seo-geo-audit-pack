---
name: ik-ai-visibility-baseline
version: 0.1.0
description: "First structured measurement of how a business (or a personal brand) shows up in AI-assistant answers — the baseline every later measurement is compared with. In 3-4 short waves of 'queries out — answers back' the owner collects REAL answer texts from ChatGPT, Google AI Mode, Gemini and Perplexity; the skill digitizes each answer, runs a meta-interrogation of the assistants, and writes the baseline report: warm and cold zones, who is recommended instead, what the assistants invent, three priorities. Never simulates answers. Triggers: /ik-ai-visibility-baseline, 'AI visibility baseline', 'starting AI visibility measurement', 'does ChatGPT recommend me', 'who do AI assistants recommend instead of us'."
---

# `/ik-ai-visibility-baseline` — the baseline of AI-assistant visibility

The baseline is valuable because it is honest, not because it is complete. Every later measurement (`ik-ai-visibility-recheck`) is compared with it.

Talk to the owner in their language and without internal labels of this protocol. All counting and bookkeeping is on your side; the owner only copies, pastes and switches windows.

## 0. Preconditions

- **Business profile.** Needed: who the customers are, what the business wants from AI visibility, which market(s) and languages, whether it is a personal brand, which facts are true (services, places, founding year). Look for an existing profile in the project (`ai-visibility/profile.md`). None → collect it in a short interview and save it; never invent facts, never start "roughly for now".
- **One business = one project.** Never reuse another business's profile or measurements.
- **Deep reasoning.** Run this protocol with deep reasoning enabled (extended thinking; in ChatGPT the High/Thinking mode). Analysis made in a fast/instant mode is invalid, not "slightly worse". If it already happened, do not restart: switch to deep mode, go over the material again, find gaps, ask follow-ups and complete it.
- **Collection conditions.** Private/incognito browser window, not logged in to any account.
- **Where to measure** (in this order, by real usage): **ChatGPT**, **Google AI Mode** (AI answers in Google search; the AI Mode tab or `&udm=50` on the results URL), **Gemini**, **Perplexity** (answers guests: close the login pop-up with the cross and the query goes through). Assistants that require login (at the time of writing Kimi, Grok, Claude) are either measured by the operator in their own account or marked **not measured** — a not-measured system is removed from the denominator and is never counted as "not mentioned".
- **How answers come back.** The full answer text, preceded by one line `System — query`. Partial batches are fine. If an agent with a browser does the field work, the same conditions apply; never solve CAPTCHAs.

## 1. Wave 1 — the first slice

From the profile write **8-12 queries** a real customer would ask an AI assistant, covering:
1. **direct commercial** — "who does X in <city>";
2. **comparison** — "X or Y — what to choose";
3. **best-of** — "the best X for …";
4. **identity** (only for a personal brand or a named method) — "who is <name>".

If the market has more than one language, split the queries across those languages: customers search in each, and the answers often differ.

Give the queries as a numbered list ready to copy, plus two lines of instructions: open a private window; run every query in ChatGPT, Google AI Mode, Gemini and Perplexity as a guest; paste each answer back signed `System — query`.

**Stop. Wait.** Analyse nothing until answers arrive.

## 2. Digitize wave 1, then wave 2

For every pasted answer record the **answer snapshot** (six fields), separately per system so platform differences stay visible:
1. business mentioned — yes / no;
2. cited with a link — yes / no;
3. prominence — first / in a list / in passing;
4. who was named instead;
5. tone toward the business, if mentioned;
6. fabrications about the business.

With TypeSafe available, score fields 1, 3 and 5 with `ik-typesafe` and `questions/geo-answer-scoring.json` (fill `context.business`; calibrate first); check the rest by hand.

Give the owner a 2-4 line interim view: where they already appear, who dominates their queries, what was unexpected. Visible progress keeps the work alive.

Then wave 2, built on what wave 1 showed: refined queries for promising zones **plus a meta-interrogation** — for 2-3 queries where competitors were named, the owner asks the same assistant: "Why did you recommend exactly them?" and "What would have to change for you to recommend <business>?". Same pasting format.

**Stop. Wait.**

## 3. Conditional wave 3

Apply the **sufficiency test**. The map is sufficient when all four hold:
- the main competitors are clear for every zone;
- warm and cold zones can be told apart;
- at least one meta-interrogation answer explains WHY the leaders lead;
- fabrications are checked.

Sufficient → go to the report and tell the owner why no extra wave is needed. Not sufficient → one short final wave of 3-5 queries aimed exactly at the missing point. **Hard limit: four waves in total.** The map need not be perfect; it must be honest.

## 4. Baseline report

Ask the date if it cannot be determined reliably. Append (never overwrite) a block to `ai-visibility/measurement-log.md` in the project:

```
## MEASUREMENT <YYYY-MM-DD> — BASELINE
- Systems: … (not measured: …)
- Queries: N

| Query | System | Mentioned | How (position / context) | Cited with link | Named instead | Tone | Notes |
|---|---|---|---|---|---|---|---|

- Visibility: X mentions out of Y answers (Z%) — measured systems only

### WARM ZONES        (where the business already appears)
### COLD ZONES        (where it is absent)
### WHO INSTEAD OF YOU (competitors per zone, with frequency)
### FABRICATIONS      (what the assistants invented, quoted)
### WHAT IT MEANS — three priorities
### THREE OBSERVATIONS TO DISCUSS
```

Write the report in the owner's language (the headings above may be translated). "Notes" carries fabrications and other observations per answer.

**Three priorities**, each tied to one axis of AI visibility:
- **entity** — one unambiguous identity of the business that the assistants can recognise and trust;
- **breadth** — independent mentions of the business on other sites;
- **depth** — the business's own content that the assistants quote as a primary source.

## Hard rules

- Analyse ONLY answer texts the owner (or the collecting agent) actually pasted. Never simulate, guess or "recall" what an assistant would answer. No pasted text → no table row.
- An empty zone is an honest result, not a failure to soften. No consolation edits.
- No optimisation advice inside this protocol. Conclusions are stated as the three axes above; fixing happens in separate work. Single exception: quick technical-access flags (for example the site is closed to crawlers) — name them as "pass to the developer".
- Suspiciously high results everywhere almost always mean the frame silently narrowed (one region, one niche): ask in which geographic and topical frame the assessment was made, give the real planned scale, and re-check the disputed queries.
- No fact about the business that is not in the profile or in the pasted answers.

## Self-check before closing

- [ ] A profile existed before wave 1 (or was collected and saved first).
- [ ] Every table row comes from a pasted answer text; none simulated or recalled.
- [ ] Wave 1 had 8-12 queries covering all relevant types; multilingual markets are split across languages.
- [ ] Private window, no login; the list of systems (and of not-measured ones) is recorded.
- [ ] All six snapshot fields are filled for every answer, per system.
- [ ] At least one meta-interrogation answer explains why the leaders lead.
- [ ] Competitors named per zone; warm and cold zones distinguished; fabrications checked and listed separately.
- [ ] No more than four waves.
- [ ] Empty zones shown as they are; no optimisation advice except access flags.
- [ ] Three priorities, each tied to entity / breadth / depth.
- [ ] The block is appended to `ai-visibility/measurement-log.md` under a dated heading.

## What to tell the owner at the end

The baseline is saved in the log, and every later measurement is compared with it. Next step: a repeat measurement (`ik-ai-visibility-recheck`) — monthly by default (every two weeks in an active phase) — with the same queries, the same systems and the same conditions. What was found is fixed in separate work along the three axes, not inside this protocol.
