# User data and private settings (outside the pack, survive every update)

The pack never stores user data. Everything personal lives in the user's home directory:

| Path | What |
|---|---|
| `~/.config/ik-seo-geo-audit/local.md` | optional private settings (free text + one JSON block, below) |
| `~/.config/ik-seo-geo-audit/state/last-diagnose.json` | the latest diagnostics (written by `scripts/diagnose.py`) |
| `~/.config/ik-seo-webmaster/local.md` | private notes for Search Console/Bing access (own MCP server, accounts, known failures) |
| `~/.config/ik-typesafe/questions/`, `calibrations.md` | own question sets and the calibration log |
| `~/.config/skill-update/registry.json` | provenance of third-party skills for `skill-update` |
| `~/.config/typesafe/api_key` | the TypeSafe key (never printed) |
| `<project>/seo-audit/<slug>/<date>/` | every audit's brief, data, reports and plan |
| `<project>/ai-visibility/` | AI-visibility measurements and their log |

## `local.md` JSON block

The skill reads the first fenced `json` block of `local.md`:

```json
{
  "extra_methodology": ["/abs/path/my-prioritisation-rules.md"],
  "geo_sources": ["/abs/path/my-geo-method/measurement-protocol.md"],
  "measurement_skills": {"baseline": "my-own-baseline-skill", "recheck": "my-own-recheck-skill"},
  "dashboard": "orq",
  "handoff_outbox": "/abs/path/graphify/outbox"
}
```

- `extra_methodology` — your own rule files, read with the same gate as the shipped methodology.
- `geo_sources` — private GEO method files given to the GEO auditor (#18).
- `measurement_skills` — use your own measurement skills instead of `ik-ai-visibility-baseline/recheck`.
- `dashboard: "orq"` — mirror progress to a local `orq` dashboard in addition to `status.md`.
- `handoff_outbox` — also copy `handoff.md` into this folder (e.g. a second-brain inbox).

Anything not in the JSON block is ignored by scripts but read by the agent as context.
