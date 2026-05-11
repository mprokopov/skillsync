---
name: skill-manager
description: Manage portable AI agent skills and lightweight skill-adjacent tools with the skillsync CLI. Use when asked to scan, validate, convert, install, sync, or troubleshoot skills across Claude Code, OpenClaw, Pi skills, or Syncthing-backed skill folders.
---

# Skill Manager

Use `scripts/skillsync` from this skill when available. It delegates to the installed `skillsync` CLI, or to this repository's source checkout if the skill lives inside the `skillsync` repo.

## Defaults

- Shared root: `$SKILLSYNC_HOME`, usually `~/Personal/AI`.
- Skill root: `$SKILLSYNC_HOME/skills`.
- Tool root: `$SKILLSYNC_HOME/tools`.
- Prefer symlinks on Maksym's own machines.
- Use copy mode for packaging, external machines, or tools that dislike symlinks.

## Common workflows

### Scan for existing skills and Claude commands

```bash
scripts/skillsync scan /path/to/repo
```

### Validate a skill

```bash
scripts/skillsync validate ~/Personal/AI/skills/projects/writebook
```

Look for missing frontmatter, broken links, likely secrets, absolute paths, and missing declared dependencies.

### Convert a Claude command into a portable skill

```bash
scripts/skillsync convert-command \
  .claude/commands/writebook.md \
  --to ~/Personal/AI/skills/projects/writebook \
  --name writebook
```

Review the generated `SKILL.md` afterwards. Convert command-style instructions into skill-style reusable procedure.

### Install into Claude Code repo-local skills

```bash
cd /path/to/repo
scripts/skillsync install ~/Personal/AI/skills/projects/writebook \
  --target claude-code \
  --scope repo \
  --mode symlink
```

Creates `.claude/skills/<name>`.

### Install into Claude Code global skills

```bash
scripts/skillsync install ~/Personal/AI/skills/projects/writebook \
  --target claude-code \
  --scope global \
  --mode symlink
```

Creates `~/.claude/skills/<name>`.

### Install into OpenClaw workspace skills

```bash
scripts/skillsync install ~/Personal/AI/skills/projects/writebook \
  --target openclaw \
  --mode symlink
```

Creates `~/.openclaw/workspace/skills/<name>`.

### Install lightweight companion tools

```bash
scripts/skillsync tool list
scripts/skillsync tool install writebook --mode symlink
```

By default, tool binaries install into `~/.local/bin`.

## Scope rules

Supported scopes:

- `repo` — current repository/project.
- `global` — user-level agent location where supported.

Target behavior:

- `claude-code` + `repo` → `.claude/skills/<name>`
- `claude-code` + `global` → `~/.claude/skills/<name>`
- `pi` + `repo` → `.pi/skills/<name>`
- `openclaw` → `~/.openclaw/workspace/skills/<name>` regardless of scope for now

Use `--dest PATH` to bypass target/scope resolution.

## Safety

- Do not sync secrets or config files as part of a skill.
- Public skills must not contain private paths, tokens, account IDs, or personal context.
- Treat Syncthing conflict files (`*.sync-conflict-*`) as blockers; resolve manually before installing.
- Ask before overwriting a non-symlink skill directory with meaningful local changes.
