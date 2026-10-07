# Changelog

All notable changes to this pack. Versions follow [Semantic Versioning](https://semver.org/); every published version has a git tag `vX.Y.Z`.

## [0.1.0] - 2026-10-07
First public beta, built from a real 18-auditor audit of a production site.
### Added
- `ik-seo-geo-audit` master skill: diagnostics of required skills (installed / current on GitHub) and of access (Search Console, Bing, browser, optional services); setup master prompts (install / update / connect); interview via `grilling`; the autonomous audit master prompt; recurring-audit reminder (calendar connector or `.ics`).
- Multi-host projects: one audit for several domains/subdomains with a shared crawl cache, a URL limit with honest sampling, and cross-host checks.
- Shipped prioritisation methodology (triage + plan rules, each backed by at least three quoted skills; configurable defaults D1-D12).
- `ik-seo-webmaster`: Search Console and Bing through an MCP server when present, otherwise through the browser (incl. the full not-indexed list per reason).
- `ik-typesafe` with the `jev` CLI and generic question sets (`seo-finding-triage`, `geo-answer-scoring`).
- `ik-ai-visibility-baseline` and `ik-ai-visibility-recheck`: AI-assistant visibility measurement in waves with real answers only, and dynamics across all measurements.
- `skill-update`: security-reviewed updates of third-party skills (registry moved to `~/.config/skill-update/`).
- `scripts/publish.sh` + `scripts/scan_private.py`: secret/private-data scan, version bump, changelog, tag, push.
