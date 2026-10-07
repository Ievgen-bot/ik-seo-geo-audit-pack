---
name: ik-ai-visibility-recheck
version: 0.1.0
description: "Every AI-visibility measurement after the baseline: re-runs the SAME queries in the same assistants under the same conditions, digitizes the real answers with the same six-field snapshot, and reports the movement against the actual previous report plus the trend across ALL earlier measurements — what appeared, strengthened, stayed, disappeared; likely causes; changes in who is recommended instead; updated priorities. Triggers: /ik-ai-visibility-recheck, 'repeat AI visibility measurement', 'remeasure AI visibility', 'monthly AI visibility check', 'did AI answers change'."
---

# `/ik-ai-visibility-recheck` — repeat measurement and dynamics

The result is not a new baseline but a **dynamics report**: the movement relative to the real previous measurement and the trajectory across the whole history. Talk to the owner in their language and without internal labels.

## 0. Preconditions

- A completed baseline made with `ik-ai-visibility-baseline`. This protocol applies only to measurements after the first one.
- The measurement history in the project's `ai-visibility/measurement-log.md`: at least the latest report, ideally all of them — the reports themselves, never a retelling from memory. No history available → say so plainly and ask the owner to paste the previous report(s). Do not start comparing until the real previous report is in front of you.
- The business profile, to see whether the business changed (new services, new markets) and whether that justifies new queries.
- Timing: changes are checked about a month after they were published, not "the next day". Until the control measurement the honest status of a fix is "published, waiting for check".
- Deep reasoning on; the same collection conditions as the baseline (private window, no login, the same systems; not-measured systems stay out of the denominator).

## 1. Find the history

Read every block in `ai-visibility/measurement-log.md` (both BASELINE and DYNAMICS), order them by date — this is the history the trend is built on. Confirm to the owner in one line what was found ("I see N measurements: <dates>") and that the point of direct comparison is the latest one.

**Stop** if there is no history: wait until the owner provides the reports.

## 2. Re-run the same queries

Give the **same queries** as the baseline, as a numbered list ready to copy. Add 2-3 new queries only when the profile or the owner shows the business changed — and say why. Field instructions are inherited: private window, the same systems, every answer pasted back with the line `System — query`, partial batches fine.

**Stop. Wait.** Analyse nothing until answers arrive. One round of queries, then the comparison; a second short round only if the first revealed something new worth probing.

## 3. Dynamics report

Digitize every answer with the same six-field snapshot as the baseline (mentioned · cited with link · prominence first / list / passing · named instead · tone · fabrications), per system. Then append (never overwrite) a block to `ai-visibility/measurement-log.md`:

```
## MEASUREMENT <YYYY-MM-DD> — DYNAMICS
- Systems: … (not measured: …) · Queries: N (new: …, why)

| Query | System | Mentioned | How | Cited with link | Named instead | Tone | Notes |
|---|---|---|---|---|---|---|---|

- Visibility: X of Y answers (Z%) — previous: X' of Y' (Z'%)

### WHAT CHANGED          appeared / strengthened / no movement / disappeared — per zone and per system, vs the latest measurement
### TREND ACROSS ALL MEASUREMENTS   the trajectory of each zone through all dates, as a compact strip
### LIKELY CAUSES          movement tied to actions taken since the baseline; uncertain links marked as assumptions
### WHO INSTEAD OF YOU — CHANGES
### UPDATED PRIORITIES     three, each tied to an axis: entity / breadth / depth
```

End with the date of the next measurement.

## Hard rules

- Analyse only answer texts actually pasted; never simulate, guess or recall.
- Compare only with the real previous report, never with a reconstruction of what "was probably there".
- Build the trend across ALL measurements found, not only the latest one.
- Empty zones stay empty; do not soften them.
- Suspiciously high results everywhere → check the frame (region, topic) before reporting.

## Self-check

- [ ] History found in the file; the owner was told how many measurements and which dates.
- [ ] The point of direct comparison (the latest measurement) is named.
- [ ] The comparison uses the real text of the previous report.
- [ ] Queries are the baseline ones; any new ones (2-3) are justified by a change in the business.
- [ ] Every analysed answer was actually pasted; none simulated.
- [ ] All six snapshot fields per answer, per system.
- [ ] All five dynamics sections present; the trend uses all measurements (when more than one earlier exists).
- [ ] Uncertain causal links are marked as assumptions; empty zones shown as empty.
- [ ] Three updated priorities tied to the axes; the next measurement date is named.

## What to tell the owner at the end

The measurement is in the log; the next one follows the cadence (monthly by default, every two weeks in an active phase) with the same queries and this same protocol.
