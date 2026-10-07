# Connecting services (stage A) — what to tell the user when something is missing

For every missing service produce a short instruction plus, where the setup can be done by an agent, a master prompt for a NEW chat. Never ask the user to paste a key, password or token into the chat. Keys travel only through the clipboard into a file outside every project and repository.

## Safe key handover (the only allowed way)
1. The user copies the key in the provider's console.
2. The user writes in chat: "the <service> key is in the clipboard".
3. The agent saves it without printing it:
   - macOS: `mkdir -p ~/.config/<service> && pbpaste > ~/.config/<service>/api_key && chmod 600 ~/.config/<service>/api_key`
   - Linux: the same with `xclip -o -selection clipboard` or `wl-paste` instead of `pbpaste`
4. The agent verifies the key with a free call (for TypeSafe: `jev ping`) and reports only "works / does not work".
Never echo, log or commit the key; never put it into a prompt for another model.

## Services

| Service | Needed for | How to connect | Can an agent do it? |
|---|---|---|---|
| Browser with the user's logins | Search Console and Bing UI (excluded-URL lists, URL inspection) | Built-in browser pane of the Claude desktop app, or Chrome Web Store → "Claude" by Anthropic (Claude in Chrome) → sign in → allow it for Claude Code | The user installs and logs in; the agent checks by opening the GSC property list |
| Google Search Console | indexing state, queries | Log in in that browser with the Google account that owns (or has full access to) the property. Optional: any MCP server exposing GSC tools | The user logs in; the agent verifies |
| Bing Webmaster Tools | Bing index, crawl | https://www.bing.com/webmasters → sign in → add/verify the site (import from GSC is the fastest) | Verification changes DNS/HTML of the site → the user's own action |
| GitHub CLI `gh` | version checks with a higher rate limit (optional) | `brew install gh` (macOS) / distro package; `gh auth login` | The user runs `gh auth login` (browser flow) |
| TypeSafe (`jev`) | calibrated triage of findings (optional) | https://typesafe.ai → console → API key → safe key handover to `~/.config/typesafe/api_key` | After the handover the agent runs `jev ping` |
| Semdash or other paid SEO data (optional) | keywords, backlinks, competitors | Connect it as an MCP connector in Claude (claude.ai → Settings → Connectors, or `/mcp`), then set a credit budget in the interview | Connecting is the user's action; the agent only reads with the budget |
| Google Calendar connector (optional) | recurring audit reminder | claude.ai → Settings → Connectors → Google Calendar | Without it the agent writes an `.ics` file instead |

## Master prompt template (for a new chat that connects one service)

```
This is a new chat. Task: connect <SERVICE> for the SEO/GEO audit pack, nothing else.
1. Tell me exactly where to sign up / log in and what to click (short numbered steps), then wait.
2. When I say "the key is in the clipboard", save it with the safe key handover from
   skills/ik-seo-geo-audit/references/services.md (never print it), then verify with a free call.
3. Report "works / does not work" and the next step. Do not change anything else.
```
