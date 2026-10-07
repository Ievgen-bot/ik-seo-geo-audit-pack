# ik-seo-geo-audit-pack

A skill pack for **Claude Code** that prepares and runs a full **SEO + GEO** (AI-search visibility) audit of a website project — one or several domains and subdomains audited together.

You type `/ik-seo-geo-audit`. The master skill:

1. **Diagnoses your machine.** Are the required skills installed and current on GitHub? Can it reach Google Search Console, Bing Webmaster Tools and a browser with your logins? If something is missing or outdated it gives you a ready **master prompt for a new chat** that installs, updates or connects exactly that.
2. **Interviews you** (with the `grilling` skill): which hosts belong to the project, what the business sells and where, what is deliberately closed, which recommendations are off-limits, which access exists, full or light audit.
3. **Hands over one big master prompt.** Pasted into a new chat, it runs the audit autonomously: inventory (including the full Search Console "not indexed" list, every URL classified), 6-18 independent auditors working from one crawl cache, triage of all findings by a shipped methodology, and a step-by-step `PLAN.md`. It never changes your sites, Search Console, Bing or servers.

Tested on Claude Code 2.1 (CLI and desktop app), macOS.

## Install

Primary — as a Claude Code plugin marketplace (updates arrive through Claude Code):

```bash
claude plugin marketplace add Ievgen-bot/ik-seo-geo-audit-pack
claude plugin install ik-seo-geo-audit@ik-seo-geo-audit-pack
```

Fallback — a git clone, linking the skills into your skills folder:

```bash
git clone https://github.com/Ievgen-bot/ik-seo-geo-audit-pack.git ~/dev/ik-seo-geo-audit-pack
for s in ~/dev/ik-seo-geo-audit-pack/skills/*; do ln -s "$s" ~/.claude/skills/; done
```

Then start Claude Code in your project folder and run `/ik-seo-geo-audit`. The first run tells you which third-party skills to install; you can also install them upfront:

```bash
claude plugin marketplace add searchfit/searchfit-seo && claude plugin install searchfit-seo@searchfit-seo
claude plugin marketplace add anthropics/knowledge-work-plugins && claude plugin install marketing@knowledge-work-plugins && claude plugin install small-business@knowledge-work-plugins
claude plugin marketplace add coreyhaines31/marketingskills && claude plugin install marketing-skills@marketingskills
claude plugin marketplace add nowork-studio/notfair-plugin && claude plugin install notfair@nowork-studio
claude plugin marketplace add mattpocock/skills && claude plugin install mattpocock-skills@mattpocock
```

## What is inside

| Skill | What it does |
|---|---|
| `ik-seo-geo-audit` | the master: diagnostics → interview → master prompt; scripts for crawling, classification, merging findings; the auditors workflow; the methodology |
| `ik-seo-webmaster` | Search Console + Bing through an MCP server if you have one, otherwise through the browser (full not-indexed list per reason, URL inspection, sitemaps) |
| `ik-typesafe` | bulk typed judgments with TypeSafe (`jev` CLI): calibrated triage of hundreds of audit findings (optional, needs a key) |
| `ik-ai-visibility-baseline` | the first measurement of how AI assistants answer your customers' questions — real answers only, in waves, with a meta-interrogation |
| `ik-ai-visibility-recheck` | every later measurement: same queries, dynamics against all earlier measurements |
| `skill-update` | updates third-party skills only after a security review, keeping your local edits |

Third-party skills used by the auditors are **not** copied into this repository; each user installs them from their upstream repositories (see `skills/ik-seo-geo-audit/manifest/skills.json`).

## Your data stays yours

Nothing personal is stored in the pack. Settings, keys, question sets and registries live in `~/.config/…`; audits are written into your project folder (`seo-audit/<project>/<date>/`). Updating the pack never touches them. Keys are handed over only through the clipboard into `~/.config/<service>/`, never pasted into chat. See `skills/ik-seo-geo-audit/references/local-config.md`.

## Updating

Marketplace install: `claude plugin marketplace update ik-seo-geo-audit-pack && claude plugin update ik-seo-geo-audit@ik-seo-geo-audit-pack`. Git clone: `git pull`. The master skill checks the pack version and every third-party skill against GitHub on each run and tells you what to update.

## Contributing / releases

Releases follow semantic versioning with a `CHANGELOG.md` entry and a `vX.Y.Z` tag. Before every publication `scripts/publish.sh` scans the repository for secrets and private data and refuses to publish on any hit.

## Credits

The audit builds on these skills (installed separately; short quotations in the methodology are attributed):
[searchfit/searchfit-seo](https://github.com/searchfit/searchfit-seo) (MIT) ·
[anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) — marketing, small-business (Apache-2.0) ·
[coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) (MIT) ·
[nowork-studio/notfair-plugin](https://github.com/nowork-studio/notfair-plugin) (MIT) ·
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT) ·
[blader/humanizer](https://github.com/blader/humanizer) (MIT, optional).

## License

Apache-2.0 — see `LICENSE` and `NOTICE`.

Author: Ievgen Kovalevskyi — [ikovalevskyi.com](https://ikovalevskyi.com)
