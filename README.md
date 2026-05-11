# skillsync

Tiny local helper for syncing AI agent skills and lightweight tools across machines.

Designed for a Syncthing-style shared folder plus thin installs into agent-specific locations:

- Claude Code repo/global skills
- OpenClaw workspace skills
- project-local `.pi/skills`
- lightweight scripts in `tools/*/bin`

## Install locally

```bash
ln -sfn "$PWD/bin/skillsync" ~/.local/bin/skillsync
```

## Default layout

```text
~/Personal/AI/
  skills/
    public/
    personal/
    projects/
  tools/
    skillsync/bin/skillsync
    writebook/bin/writebook
```

Set another root with:

```bash
export SKILLSYNC_HOME="$HOME/Personal/AI"
```

## Commands

```bash
skillsync scan PATH
skillsync validate PATH
skillsync convert-command .claude/commands/foo.md --to skills/foo
skillsync install skills/foo --target claude-code --scope repo --mode symlink
skillsync tool list
skillsync tool install writebook --mode symlink
```

## Status

MVP. Boring on purpose.
