---
name: skill-update
version: 0.1.0
description: "Update third-party agent skills downloaded from GitHub, with a security review BEFORE anything is installed. Asks the scope (all / named skills / topic / repo), splits skills into shards for sub-agents, checks the new upstream version (full-tree scan, diff, history), applies only reviewed-safe changes with backups, keeps your local edits via 3-way merge, and lists the problematic ones. Triggers: /skill-update, 'update skills', 'check for skill updates', 'update skills from GitHub'."
---

# Skill Update

All paths below are relative to `SK` = the directory of this skill. The provenance registry (which upstream repo/path each skill comes from) is user data and lives outside the skill: `~/.config/skill-update/registry.json` (override with `$SKILL_UPDATE_REGISTRY`); it is created empty on first use. Agent protocol: `$SK/PROTOCOL.md`.

## 0. Scope — ALWAYS ask first (AskUserQuestion), run nothing before the answer
```bash
python3 "$SK/scripts/plan_run.py" --list
```
Options: all (`--all`) · named (`--skills a,b`) · topic (`--topic "seo schema"`) · repo (`--repo owner/name`). Show the `--dry` selection and get an explicit "yes":
```bash
python3 "$SK/scripts/plan_run.py" --skills geo-optimizer,ai-seo --dry
```
Skill families are added as a whole. Skills deleted upstream are skipped.

## 1. Plan → RUN dir (no spaces in the path, `~/.agents/skill-update-runs/…`)
`plan_run.py <same selection>` without `--dry` prints `RUN DIR`.

## 2. Agents
One background Agent (general-purpose) per `RUN/prompts/sNN.txt` (file content = prompt), all in one message. If an agent is silent for >30 min, message it "wrap up, unfinished = ERROR".

## 3. Review and decisions
```text
python3 RUN/tools/post_process.py RUN --write        # copies: identical / stale_pristine / diverged
python3 RUN/tools/aggregate.py RUN
python3 RUN/tools/decide.py RUN show
```
Orchestrator checklist (hold even if the agent said SAFE via `decide.py RUN hold a,b --category … --reason …`): removed write-guards in skills that touch money or ads; behaviour against the user's own rules; new `${CLAUDE_PLUGIN_ROOT}` usage (grep in `snap/`); reading tokens or credentials; a partial update of a family that breaks references. Show the list to the user; on "yes" → `decide.py RUN accept a,b`.

## 4. Apply (dry-run → apply)
```text
python3 RUN/tools/merge3.py RUN                       # your edits + new upstream; the diff must contain ONLY your lines
python3 RUN/tools/apply_updates.py --su RUN           # dry-run
python3 RUN/tools/apply_updates.py --su RUN --apply
python3 RUN/tools/apply_merges.py RUN/merges/spec.json --apply --log RUN/apply-log-$(date +%Y%m%d-%H%M%S)-merges.json
python3 RUN/tools/apply_extra.py --su RUN --run1 RUN/apply-log-<…>-updates.json --apply   # copies inside other local clones
python3 RUN/tools/check_untouched.py RUN              # must be 0 / 0 / 0 / 0
python3 RUN/tools/finalize.py RUN --out "<project>/outputs/skills-update/<date>-<scope>"
```
Report to the user: PROBLEMS.md (the "do not update" list with reasons), rollback `RUN/rollback.sh` (dry-run; `--yes` to execute). Backups: `~/.claude/skill-sources/_backups/<date>/`.

## Gotchas
- `jev-skill-router --scan` (optional, if installed) reads only the first 6000 characters of SKILL.md and on a foreign folder may silently report `scanned: 0` — that is NOT "clean", only an extra signal. Without it the full-tree scan and diff review still run.
- Clones are NOT fast-forwarded (upstream restructures would break symlinks); updates are applied per file; `.venv` / `node_modules` are never touched.
- Root-level skills in the npx-skills lock file store a commit SHA, not a tree SHA (handled automatically).
- Plugins installed through Claude Code marketplaces or synced by the Claude app (`~/.claude/plugins`) are out of scope: the app updates them.
- zsh: write `"${U}:path"`, not `"$U:path"`.
