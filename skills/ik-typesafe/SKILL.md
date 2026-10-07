---
name: ik-typesafe
version: 0.1.0
description: "Bulk typed judgments with TypeSafe (model Jev, System One) instead of one LLM call per row: classify, score or check dozens to thousands of similar records (audit findings, AI-assistant answers from visibility measurements, search terms, reviews, leads, titles). CLI `jev` (Python stdlib, no SDK), ready question sets in `questions/`, mandatory calibration >= 90% on labelled examples before production. Triggers: /ik-typesafe, 'run it through TypeSafe', 'via jev', 'classify / score N rows', 'triage audit findings', 'score AI answers from the measurement'."
---

# `/ik-typesafe` — bulk typed judgments with TypeSafe (Jev)

TypeSafe is not analytics and not a text generator. It is an API that answers a **typed question** about a given `state` with a **number**: `noul` (probability of "yes"), `choice` (option + distribution + confidence), `score` (position on a scale + confidence). About 1 s per request, cents per row. Use it for **thousands of identical decisions in code**, not for one answer in chat. Code owns the process; Jev only judges. Conclusions, reports and texts are yours.

## When to use it

Use it when there are N >= ~30 similar records and each needs the same narrow decision. Do NOT use it to write text, research, calculate, or answer a single question, and never for data the owner forbids sending to a third party.

| Need | Primitive | Ready set |
|---|---|---|
| Triage findings of a multi-agent SEO/GEO audit (evidence? unmeasured claim? area? severity?) | noul + choice | `questions/seo-finding-triage.json` |
| Score an AI-assistant answer from a visibility measurement (mentioned? prominence? type? tone?) | noul + choice | `questions/geo-answer-scoring.json` |

Your own question sets (client-specific, private) live outside this skill in `~/.config/ik-typesafe/questions/` so that skill updates never touch them.

## Key

`jev` looks for the key in this order: `$TYPESAFE_API_KEY` → `~/.config/typesafe/api_key` → `~/.config/typesafe/env` → the file in `$TYPESAFE_API_KEY_FILE`. Never print the key, never put it in a project or a repository.

No key: `jev ping` says `API key not found`. Getting a key is the user's action (see "Getting a key" below); the skill never asks the user to paste a key into chat.

### Getting a key (operator steps)
1. Sign up at https://typesafe.ai and create an API key in the console (https://console.typesafe.ai/keys).
2. Copy the key to the clipboard and tell the agent: "the TypeSafe key is in the clipboard".
3. The agent saves it without printing: `mkdir -p ~/.config/typesafe && pbpaste > ~/.config/typesafe/api_key && chmod 600 ~/.config/typesafe/api_key` (Linux: `xclip -o -selection clipboard` or `wl-paste` instead of `pbpaste`), then runs `jev ping`.

## Install the CLI

```
ln -sf "$(pwd)/skills/ik-typesafe/bin/jev" ~/.local/bin/jev   # run from the pack root
jev --help
```

## Commands

```
jev ping                                             # key alive? model, latency, tokens
jev ask --questions Q.json --state "text or JSON"    # one judgment -> stdout
jev ask --questions Q.json --rows R.jsonl --id-field id \
        --out OUT.jsonl --max-requests 500 --dry-run # dry-run first: request count, sample state
jev ask ... --out OUT.jsonl --resume                 # continue after an interruption
jev calibrate --results OUT.jsonl --truth R.jsonl --id-field id \
        --compare q1=t_field1 q2=t_field2 --min-accuracy 0.9
jev usage --results OUT.jsonl                        # tokens of a run
```

`--rows`: JSONL or a JSON array; one row = one request. `state_fields` in the question file trims the row to the needed fields. `context` from the question file is added to every state under the key `context` (put constant facts there: the business, the rubric, the owner's decisions).

## Mandatory order

1. **Pick a set** from `questions/` (or the user's own dir). Copy it into the project folder and change only `context`. No fitting set → write a new one following `questions/README.md`.
2. **Dry-run** → show the user the number of requests and stop if it exceeds the ceiling they named. Default ceiling `--max-requests 500`.
3. **Calibrate** before the first production use of a set: 20-60 rows labelled by a human strictly by the rubric (stratify by class; add deliberately broken examples for rare classes). Every question must be >= 0.90. Below → fix wording/criteria (never the data) and repeat.
4. **Run** with `--out` and `--resume`. A `noul` near 0.5 is "undecided", not "medium": send such rows to a human or a stronger model.
5. **Log the calibration** in `~/.config/ik-typesafe/calibrations.md` (date, data, n, accuracy per question, tokens).

## Limits

- Data goes to a third party (TypeSafe). Ask the user once per new client/data owner before the first run.
- A typed answer guarantees the format, not the truth. No production without calibration.
- Never run large volumes blind: dry-run → 3 rows → ceiling.
