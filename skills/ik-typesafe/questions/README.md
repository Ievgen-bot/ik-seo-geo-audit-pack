# Question sets for `jev`

One file = one type of decision. Business facts go only into `context`; the questions stay generic.
Copy a set into the project folder before filling `context`; never edit the shipped template for one client.
Your own sets live in `~/.config/ik-typesafe/questions/` (outside the skill, survive updates).

## Format

```json
{
  "model": "jev-latest",
  "state_fields": ["field1", "field2"],
  "context": { "...": "constant facts available to every row as `context.…`" },
  "questions": {
    "id": { "type": "noul",   "instructions": "…", "criteria": {"true": "…", "false": "…"} },
    "id": { "type": "choice", "instructions": "…", "criteria": {"opt": "description", "none": "nothing fits"} },
    "id": { "type": "score",  "instructions": "…", "criteria": ["level 0", "level 1", "level 2"] }
  }
}
```

Wording rules (from the TypeSafe docs, confirmed by calibration):
- one narrow judgment per question; independent dimensions are separate questions;
- refer to the data with backticks: `answer_text`, `context.business`;
- choice options and score levels describe **concrete situations**, not adjectives;
- always provide a "not mentioned / nothing fits" exit;
- the model does not see the question ID — put all meaning into `instructions` / `criteria`.

## Shipped sets

| File | Judges | Truth fields for calibration |
|---|---|---|
| `seo-finding-triage.json` | one audit finding: `has_evidence` (noul), `unmeasured_claim` (noul), `category` (choice), `severity` (choice: critical / high / medium / low / not_an_issue) | `t_has_evidence`, `t_unmeasured_claim`, `t_category`, `t_severity` |
| `geo-answer-scoring.json` | one AI-assistant answer: `mentioned` (noul), `prominence` (first / list / passing / none), `answer_type` (transactional / informational), `tone` | `mentioned`, `prominence`, `answer_type`, `tone` |

Reference calibration of `seo-finding-triage` (2026-10-05, one real audit, n = 30 including 12 deliberately broken rows): has_evidence 0.967 · unmeasured_claim 1.0 · category 0.933 · severity 1.0. Recalibrate on your own data.
