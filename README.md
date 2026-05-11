# skillsync

Tiny local helper for syncing AI agent skills and lightweight tools across machines.

`skillsync` assumes you already have a shared folder, usually synced with Syncthing. It does **not** try to be a cloud service or a package registry. It just validates, converts, and installs skills/tools into the places different agents expect.

## What it manages

- Claude Code repo/global skills
- OpenClaw workspace skills
- project-local `.pi/skills`
- lightweight scripts in `tools/*/bin`

## Recommended synced layout

On Maksym's machines the shared root is currently `~/Personal/AI` because `~/Personal` is already synced by Syncthing.

```text
~/Personal/AI/
  skills/
    public/
    personal/
    projects/
      writebook/
        SKILL.md
        skill.meta.json
  tools/
    skillsync/
      bin/skillsync
    writebook/
      bin/writebook
```

Set the root explicitly:

```bash
export SKILLSYNC_HOME="$HOME/Personal/AI"
```

Put that in `~/.zshrc` or `~/.bashrc` if needed.

## Install with uv

Preferred install on macOS/Linux:

```bash
uv tool install ~/Personal/AI/tools/skillsync
skillsync --help
```

If the synced folder is not available yet, install from GitHub:

```bash
uv tool install "git+https://github.com/mprokopov/skillsync.git"
```

To reinstall after updates:

```bash
uv tool upgrade skillsync
```

For editable local development, use the synced folder directly:

```bash
cd ~/Personal/AI/tools/skillsync
uv tool install --editable . --force
```

## Install lightweight tools

Example: install the generic `writebook` CLI from the synced tools tree:

```bash
skillsync tool list
skillsync tool install writebook --mode symlink
writebook --help
```

By default tools install into `~/.local/bin`.

## Common workflows

### Scan a repo

```bash
skillsync scan /path/to/repo
```

Finds existing skills and Claude command files.

### Validate a skill

```bash
skillsync validate ~/Personal/AI/skills/projects/writebook
```

Checks for:

- missing `SKILL.md`
- missing `name` / `description` frontmatter
- broken relative links
- likely secrets
- absolute local paths
- missing declared binaries or paths

### Convert a Claude command into a skill

```bash
skillsync convert-command \
  .claude/commands/writebook.md \
  --to ~/Personal/AI/skills/projects/writebook \
  --name writebook
```

This creates:

```text
SKILL.md
skill.meta.json
```

### Install a skill into Claude Code repo-local skills

```bash
cd /path/to/project
skillsync install ~/Personal/AI/skills/projects/writebook \
  --target claude-code \
  --scope repo \
  --mode symlink
```

Creates:

```text
.claude/skills/writebook -> ~/Personal/AI/skills/projects/writebook
```

### Install a skill into `.pi/skills`

```bash
cd /path/to/project
skillsync install ~/Personal/AI/skills/projects/writebook \
  --target pi \
  --scope repo \
  --mode symlink
```

Creates:

```text
.pi/skills/writebook -> ~/Personal/AI/skills/projects/writebook
```

### Install a skill into OpenClaw workspace skills

```bash
skillsync install ~/Personal/AI/skills/projects/writebook \
  --target openclaw \
  --mode symlink
```

Creates:

```text
~/.openclaw/workspace/skills/writebook -> ~/Personal/AI/skills/projects/writebook
```

## Example: setup on a new Mac

```bash
brew install uv

# Wait for Syncthing to sync ~/Personal/AI, then:
export SKILLSYNC_HOME="$HOME/Personal/AI"
uv tool install ~/Personal/AI/tools/skillsync

skillsync tool install writebook --mode symlink
writebook --help

cd ~/Developer/adminka-core
skillsync install ~/Personal/AI/skills/projects/writebook \
  --target claude-code \
  --scope repo \
  --mode symlink
```

## Privacy buckets

Suggested skill categories:

- `public` — safe to publish; no private paths, secrets, or personal data.
- `personal` — synced only between your own machines.
- `projects` — reusable inside a project/team context.
- `openclaw-only` — allowed to depend directly on OpenClaw-specific tools.

## Status

MVP. Boring on purpose.
