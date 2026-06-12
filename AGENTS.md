# AGENTS.md — skillsync contributor guide

This repo manages portable AI agent skills and lightweight companion binaries/scripts.

Use this guide when preparing a new skill, a new tool binary, or both for sync across machines.

## Core model

`skillsync` separates three things:

1. **Skill** — procedural agent instructions in `SKILL.md`.
2. **Tool** — lightweight executable script/binary in `tools/<name>/bin/`.
3. **Install location** — symlink/copy target for a specific agent or project.

Syncthing moves files between machines. `skillsync` validates and installs them locally.

Default shared root on Maksym's machines:

```text
~/Personal/AI/
  skills/
  tools/
```

## Skill layout

Create skills under the synced root:

```text
~/Personal/AI/skills/<bucket>/<skill-name>/
  SKILL.md
  skill.meta.json
  scripts/        # optional helper scripts
  references/     # optional docs loaded only when needed
  assets/         # optional output assets/templates
```

Buckets:

- `public` — safe to publish. No private paths, secrets, accounts, or personal context.
- `personal` — Maksym-only workflows synced across his machines.
- `projects` — project/team-specific reusable skills.
- `openclaw-only` — may depend directly on OpenClaw tools/features.

## `SKILL.md` rules

Every skill needs minimal YAML frontmatter:

```yaml
---
name: skill-name
description: Clear trigger description: what this skill does and when to use it.
---
```

Keep the body short and procedural:

- Say when to use the skill.
- Give exact command patterns where useful.
- Reference bundled scripts with relative paths, e.g. `scripts/do-thing`.
- Put large details into `references/` and mention when to read them.
- Avoid local absolute paths unless `privacy` is `personal`.
- Never include secrets, tokens, cookies, API keys, or real credentials.

## `skill.meta.json`

Add metadata beside `SKILL.md`:

```json
{
  "schema": "https://openclaw.ai/schemas/skill-meta-v1.json",
  "id": "skill-name",
  "privacy": "project",
  "compatibility": {
    "claude-code": true,
    "codex": true,
    "openclaw": true,
    "pi": true
  },
  "requires": [
    { "bin": "python3" },
    { "bin": "tool-name", "install": "skillsync tool install tool-name" }
  ]
}
```

Use `requires` for external binaries, repo-local paths, or companion tools.

## Tool/binary layout

Use `tools/` for lightweight companion executables that should travel with the synced setup:

```text
~/Personal/AI/tools/<tool-name>/
  bin/<tool-name>
  README.md       # optional, human-facing
```

Good tool candidates:

- small Python/Ruby/Bash scripts
- generic CLIs used by several skills/projects
- wrappers around web APIs or local workflows

Do **not** put these in `tools/`:

- secrets/config files
- large compiled binaries unless there is a strong reason
- package-manager dependencies like `git`, `gh`, `hugo`, `ffmpeg`
- project-only scripts that belong inside one repo

For package-manager dependencies, declare them in `skill.meta.json` instead.

## Preparing a new skill + tool

Example for `writebook`:

```bash
export SKILLSYNC_HOME="$HOME/Personal/AI"

mkdir -p "$SKILLSYNC_HOME/tools/writebook/bin"
cp /path/to/writebook "$SKILLSYNC_HOME/tools/writebook/bin/writebook"
chmod +x "$SKILLSYNC_HOME/tools/writebook/bin/writebook"

mkdir -p "$SKILLSYNC_HOME/skills/projects/writebook"
cat > "$SKILLSYNC_HOME/skills/projects/writebook/SKILL.md" <<'MD'
---
name: writebook
description: Browse and manage Writebook documentation using the writebook CLI.
---

Use `writebook` for listing books, reading pages, searching, and creating or editing documentation.
Prefer `--json` for commands where structured output is available.
MD

cat > "$SKILLSYNC_HOME/skills/projects/writebook/skill.meta.json" <<'JSON'
{
  "schema": "https://openclaw.ai/schemas/skill-meta-v1.json",
  "id": "writebook",
  "privacy": "project",
  "compatibility": {
    "claude-code": true,
    "codex": true,
    "openclaw": true,
    "pi": true
  },
  "requires": [
    { "bin": "ruby" },
    { "bin": "writebook", "install": "skillsync tool install writebook" }
  ]
}
JSON
```

Then validate and install:

```bash
skillsync validate "$SKILLSYNC_HOME/skills/projects/writebook"
skillsync tool install writebook --mode symlink
```

## Installing a skill into agents/projects

Claude Code repo-local:

```bash
cd /path/to/project
skillsync install "$SKILLSYNC_HOME/skills/projects/writebook" \
  --target claude-code \
  --scope repo \
  --mode symlink
```

Claude Code global:

```bash
skillsync install "$SKILLSYNC_HOME/skills/projects/writebook" \
  --target claude-code \
  --scope global \
  --mode symlink
```

Codex user skills:

```bash
skillsync install "$SKILLSYNC_HOME/skills/projects/writebook" \
  --target codex \
  --mode symlink
```

This installs to `$CODEX_HOME/skills/<name>` when `CODEX_HOME` is set, otherwise `~/.codex/skills/<name>`.

OpenClaw workspace:

```bash
skillsync install "$SKILLSYNC_HOME/skills/projects/writebook" \
  --target openclaw \
  --mode symlink
```

Pi/project skill folder:

```bash
cd /path/to/project
skillsync install "$SKILLSYNC_HOME/skills/projects/writebook" \
  --target pi \
  --scope repo \
  --mode symlink
```

Use `--dest PATH` for unsupported layouts.

## Importing an existing skill

Use `import` for an existing skill directory that already has `SKILL.md`.

Example: import Claude Code's repo-local `metabase` skill:

```bash
cd /path/to/adminka-core
skillsync import .claude/skills/metabase --bucket projects
```

This copies it to:

```text
$SKILLSYNC_HOME/skills/projects/metabase
```

Then it creates `skill.meta.json` if missing and validates the imported copy.

To replace the original with a managed symlink after import:

```bash
skillsync import .claude/skills/metabase --bucket projects --link-back
```

Use `--dry-run` first when unsure. Use `--force` only when replacing an existing destination intentionally.

## Converting an existing Claude command

```bash
skillsync convert-command \
  .claude/commands/name.md \
  --to "$SKILLSYNC_HOME/skills/projects/name" \
  --name name
```

Then edit the generated `SKILL.md`:

- remove command-only wording
- make it reusable outside one repository
- replace project-local binaries with generic tool names where appropriate
- add tool requirements to `skill.meta.json`

## Validation checklist

Before committing or syncing widely:

```bash
skillsync validate "$SKILLSYNC_HOME/skills/<bucket>/<skill-name>"
skillsync tool list
```

Check manually:

- `SKILL.md` has `name` and `description`.
- `skill.meta.json` exists and has correct `privacy`.
- Required tools are declared.
- No secrets or credentials are present.
- No accidental machine-specific absolute paths in public/project skills.
- Symlinks resolve on this machine.
- Tool runs with `--help` or equivalent.

## GitHub repo hygiene

This repo contains the `skillsync` implementation and documentation.

Before committing:

```bash
git status --short
python3 -m compileall -q src bin/skillsync
skillsync --help >/tmp/skillsync-help-ok.txt
```

Commit only intentional files. Do not commit Syncthing conflict files.
