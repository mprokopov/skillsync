#!/usr/bin/env python3
"""skillsync: tiny local skill/tool sync helper.

MVP: scan, validate, install, convert Claude commands to skills, and install
lightweight tools from a Syncthing-style root.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(os.environ.get("SKILLSYNC_HOME", "~/Personal/AI")).expanduser()
SKILL_MD = "SKILL.md"
META_JSON = "skill.meta.json"

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
]
ABS_PATH_RE = re.compile(r"/(Users|home|var|etc|opt|usr/local)/[^\s)`'\"]+")
OPENCLAW_TOOL_NAMES = {
    "browser", "cron", "message", "nodes", "session_status", "sessions_spawn",
    "memory_search", "gateway", "canvas", "image_generate", "video_generate",
}


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def rel_or_abs(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def is_skill_dir(path: Path) -> bool:
    return path.is_dir() and (path / SKILL_MD).is_file()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"\'')
    return data, body


def load_meta(skill_dir: Path) -> dict[str, Any]:
    path = skill_dir / META_JSON
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as e:
        die(f"invalid JSON in {path}: {e}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_skills(root: Path) -> list[Path]:
    if not root.exists():
        return []
    found: list[Path] = []
    for p in root.rglob(SKILL_MD):
        if ".git" in p.parts or "node_modules" in p.parts:
            continue
        found.append(p.parent)
    return sorted(set(found))


def find_commands(root: Path) -> list[Path]:
    if not root.exists():
        return []
    found: list[Path] = []
    for p in root.rglob(".claude/commands/*.md"):
        if ".git" not in p.parts:
            found.append(p)
    for p in root.rglob(".claude/commands/**/*.md"):
        if ".git" not in p.parts:
            found.append(p)
    return sorted(set(found))


def validate_skill(skill_dir: Path, privacy_override: str | None = None) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not skill_dir.exists():
        errors.append("skill directory does not exist")
    if not (skill_dir / SKILL_MD).is_file():
        errors.append("missing SKILL.md")
        text = ""
        fm: dict[str, str] = {}
    else:
        text = read_text(skill_dir / SKILL_MD)
        fm, _ = parse_frontmatter(text)
        if not fm.get("name"):
            errors.append("frontmatter missing name")
        if not fm.get("description"):
            errors.append("frontmatter missing description")

    meta = load_meta(skill_dir) if skill_dir.exists() else {}
    privacy = privacy_override or meta.get("privacy", "unknown")

    for pattern in SECRET_PATTERNS:
        if text and pattern.search(text):
            errors.append("possible secret/token in SKILL.md")
            break

    abs_paths = sorted(set(ABS_PATH_RE.findall(text))) if text else []
    # findall returns first group; use finditer for full matches
    full_abs = sorted(set(m.group(0) for m in ABS_PATH_RE.finditer(text))) if text else []
    if full_abs and privacy == "public":
        errors.append("absolute local paths found in public skill: " + ", ".join(full_abs[:5]))
    elif full_abs:
        warnings.append("absolute paths found: " + ", ".join(full_abs[:5]))

    for tool in sorted(OPENCLAW_TOOL_NAMES):
        if re.search(rf"\b{re.escape(tool)}\b", text):
            warnings.append(f"mentions OpenClaw tool name: {tool}")

    for m in re.finditer(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)", text or ""):
        target = m.group(1).split("#", 1)[0]
        if target and not (skill_dir / target).exists():
            warnings.append(f"broken relative link: {target}")

    for req in meta.get("requires", []):
        if isinstance(req, dict) and req.get("path"):
            p = skill_dir / req["path"] if req.get("scope") != "repo" else Path.cwd() / req["path"]
            if not p.exists():
                warnings.append(f"required path not found: {req['path']}")
        if isinstance(req, dict) and req.get("bin"):
            if shutil.which(req["bin"]) is None:
                warnings.append(f"required binary not on PATH: {req['bin']}")

    status = "OK" if not errors else "FAIL"
    print(f"{status} {skill_dir}")
    for e in errors:
        print(f"  error: {e}")
    for w in warnings:
        print(f"  warn: {w}")
    return 1 if errors else 0


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def install_path(src: Path, dest: Path, mode: str, dry_run: bool = False) -> None:
    src = src.resolve()
    dest = dest.expanduser()
    if not src.exists():
        die(f"source does not exist: {src}")
    if dry_run:
        print(f"would {mode}: {src} -> {dest}")
        return
    ensure_parent(dest)
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.is_dir():
            shutil.rmtree(dest)
    if mode == "symlink":
        dest.symlink_to(src, target_is_directory=src.is_dir())
    elif mode == "copy":
        if src.is_dir():
            shutil.copytree(src, dest, symlinks=True)
        else:
            shutil.copy2(src, dest)
    else:
        die(f"unknown install mode: {mode}")
    print(f"installed {src} -> {dest} ({mode})")


def copy_skill(src: Path, dest: Path, force: bool = False, dry_run: bool = False) -> None:
    if not is_skill_dir(src):
        die(f"not a skill directory: {src}")
    if dest.exists() or dest.is_symlink():
        if not force:
            die(f"destination already exists: {dest} (use --force to replace)")
        if dry_run:
            print(f"would remove existing destination: {dest}")
        elif dest.is_symlink() or dest.is_file():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    if dry_run:
        print(f"would import: {src} -> {dest}")
        return
    ensure_parent(dest)
    shutil.copytree(src, dest, symlinks=True)
    print(f"imported {src} -> {dest}")


def ensure_basic_meta(skill_dir: Path, name: str, privacy: str, source: Path, dry_run: bool = False) -> None:
    meta_path = skill_dir / META_JSON
    if meta_path.exists():
        return
    meta = {
        "schema": "https://openclaw.ai/schemas/skill-meta-v1.json",
        "id": name,
        "privacy": privacy,
        "source": {"importedFrom": str(source)},
        "compatibility": {"claude-code": True, "openclaw": True},
        "requires": [],
    }
    if dry_run:
        print(f"would create {meta_path}")
        return
    write_json(meta_path, meta)
    print(f"created {meta_path}")


def target_dest(target: str, scope: str, name: str, cwd: Path) -> Path:
    if target == "claude-code":
        return (cwd / ".claude/skills" / name) if scope == "repo" else Path("~/.claude/skills").expanduser() / name
    if target == "openclaw":
        return Path("~/.openclaw/workspace/skills").expanduser() / name
    if target == "pi":
        return cwd / ".pi/skills" / name
    die(f"unknown target: {target}")


def cmd_scan(args: argparse.Namespace) -> int:
    root = rel_or_abs(args.path)
    print(f"root: {root}")
    skills = find_skills(root)
    commands = find_commands(root)
    print("skills:")
    for s in skills:
        print(f"  {s}")
    print("claude commands:")
    for c in commands:
        print(f"  {c}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = rel_or_abs(args.path)
    if is_skill_dir(path):
        return validate_skill(path, args.privacy)
    codes = [validate_skill(p, args.privacy) for p in find_skills(path)]
    return 1 if any(codes) else 0


def cmd_install(args: argparse.Namespace) -> int:
    src = rel_or_abs(args.path)
    if not is_skill_dir(src):
        die(f"not a skill directory: {src}")
    fm, _ = parse_frontmatter(read_text(src / SKILL_MD))
    name = args.name or fm.get("name") or src.name
    dest = Path(args.dest).expanduser() if args.dest else target_dest(args.target, args.scope, name, Path.cwd())
    install_path(src, dest, args.mode, args.dry_run)
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    src = rel_or_abs(args.path)
    if not is_skill_dir(src):
        die(f"not a skill directory: {src}")
    fm, _ = parse_frontmatter(read_text(src / SKILL_MD))
    name = args.name or fm.get("name") or src.name
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-") or src.name
    root = Path(args.root).expanduser() if args.root else DEFAULT_ROOT
    dest = Path(args.dest).expanduser() if args.dest else root / "skills" / args.bucket / slug

    privacy = args.privacy or {"projects": "project"}.get(args.bucket, args.bucket)

    copy_skill(src, dest, force=args.force, dry_run=args.dry_run)
    ensure_basic_meta(dest, slug, privacy, src, dry_run=args.dry_run)

    code = 0 if args.dry_run else validate_skill(dest, privacy)

    if args.link_back:
        if args.dry_run:
            print(f"would replace source with symlink: {src} -> {dest}")
        else:
            install_path(dest, src, "symlink", dry_run=False)

    return code


def cmd_convert_command(args: argparse.Namespace) -> int:
    src = rel_or_abs(args.path)
    dest = rel_or_abs(args.to)
    if not src.is_file():
        die(f"command file not found: {src}")
    text = read_text(src)
    fm, body = parse_frontmatter(text)
    name = args.name or fm.get("name") or src.stem
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-") or src.stem
    desc = fm.get("description") or f"Use the {name} workflow."
    dest.mkdir(parents=True, exist_ok=True)
    skill_text = f"---\nname: {slug}\ndescription: {desc}\n---\n\n{body.lstrip()}"
    (dest / SKILL_MD).write_text(skill_text, encoding="utf-8")
    meta = {
        "schema": "https://openclaw.ai/schemas/skill-meta-v1.json",
        "id": slug,
        "privacy": args.privacy,
        "compatibility": {"claude-code": True, "openclaw": True},
        "requires": [],
    }
    write_json(dest / META_JSON, meta)
    print(f"converted {src} -> {dest}")
    return 0


def cmd_tool_list(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser() if args.root else DEFAULT_ROOT
    tools_dir = root / "tools"
    print(f"tools root: {tools_dir}")
    if not tools_dir.exists():
        return 0
    for p in sorted(tools_dir.iterdir()):
        if p.is_dir():
            bins = sorted((p / "bin").glob("*")) if (p / "bin").exists() else []
            suffix = " (" + ", ".join(b.name for b in bins) + ")" if bins else ""
            print(f"  {p.name}{suffix}")
    return 0


def cmd_tool_install(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser() if args.root else DEFAULT_ROOT
    tool_dir = root / "tools" / args.name
    if not tool_dir.exists():
        die(f"tool not found: {tool_dir}")
    bin_dir = tool_dir / "bin"
    if not bin_dir.exists():
        die(f"tool has no bin directory: {bin_dir}")
    dest_dir = Path(args.dest).expanduser() if args.dest else Path("~/.local/bin").expanduser()
    for src in sorted(bin_dir.iterdir()):
        if src.is_file():
            install_path(src, dest_dir / src.name, args.mode, args.dry_run)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="skillsync")
    p.add_argument("--root", default=None, help="Syncthing AI root; default $SKILLSYNC_HOME or ~/Personal/AI")
    sub = p.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan")
    scan.add_argument("path", nargs="?", default=".")
    scan.set_defaults(func=cmd_scan)

    val = sub.add_parser("validate")
    val.add_argument("path")
    val.add_argument("--privacy", choices=["public", "project", "personal", "openclaw-only"])
    val.set_defaults(func=cmd_validate)

    inst = sub.add_parser("install")
    inst.add_argument("path")
    inst.add_argument("--target", choices=["claude-code", "openclaw", "pi"], default="claude-code")
    inst.add_argument("--scope", choices=["repo", "global"], default="repo")
    inst.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    inst.add_argument("--dest")
    inst.add_argument("--name")
    inst.add_argument("--dry-run", action="store_true")
    inst.set_defaults(func=cmd_install)

    imp = sub.add_parser("import", help="Import an existing skill into the synced skills root")
    imp.add_argument("path", help="Existing skill directory containing SKILL.md")
    imp.add_argument("--bucket", default="projects", choices=["public", "personal", "projects", "openclaw-only"], help="Destination bucket under $SKILLSYNC_HOME/skills")
    imp.add_argument("--privacy", choices=["public", "project", "personal", "openclaw-only"], help="Privacy value for generated skill.meta.json; defaults from bucket")
    imp.add_argument("--name", help="Destination skill name; defaults from frontmatter name or source directory")
    imp.add_argument("--dest", help="Explicit destination directory; bypasses bucket/name")
    imp.add_argument("--force", action="store_true", help="Replace existing destination")
    imp.add_argument("--link-back", action="store_true", help="Replace original source with symlink to imported skill after successful import")
    imp.add_argument("--dry-run", action="store_true")
    imp.set_defaults(func=cmd_import)

    conv = sub.add_parser("convert-command")
    conv.add_argument("path")
    conv.add_argument("--to", required=True)
    conv.add_argument("--name")
    conv.add_argument("--privacy", default="project", choices=["public", "project", "personal", "openclaw-only"])
    conv.set_defaults(func=cmd_convert_command)

    tool = sub.add_parser("tool")
    tool_sub = tool.add_subparsers(dest="tool_cmd", required=True)
    tl = tool_sub.add_parser("list")
    tl.set_defaults(func=cmd_tool_list)
    ti = tool_sub.add_parser("install")
    ti.add_argument("name")
    ti.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    ti.add_argument("--dest")
    ti.add_argument("--dry-run", action="store_true")
    ti.set_defaults(func=cmd_tool_install)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
