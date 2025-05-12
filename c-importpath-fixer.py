#!/usr/bin/env python3
"""
c-importpath-fixer:
Fixes #include "@/..." directives in C/C++ source files by replacing them
with correct relative paths from the file to the project root.

Author: github.com/BaseMax
License: MIT
"""

import os
import re
import argparse
from pathlib import Path
from shutil import copyfile
from difflib import unified_diff

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    USE_COLOR = True
except ImportError:
    USE_COLOR = False

INCLUDE_PATTERN = re.compile(r'#include\s+"@/(.+?)"')
DEFAULT_EXTENSIONS = ('.c', '.h', '.cpp', '.hpp', '.cc', '.cxx')

MISSING_INCLUDES = []

def log(msg, level="info", verbose=False):
    if not USE_COLOR:
        if level != "debug" or verbose:
            print(msg)
        return
    colors = {
        "info": Fore.CYAN,
        "warn": Fore.YELLOW,
        "error": Fore.RED,
        "success": Fore.GREEN,
        "update": Fore.MAGENTA,
        "debug": Fore.LIGHTBLACK_EX,
    }
    if level != "debug" or verbose:
        print(colors.get(level, Fore.WHITE) + msg + Style.RESET_ALL)

def find_source_files(root_dir: Path, extensions, exclude_dirs):
    exclude_dirs = [root_dir / Path(p).resolve().relative_to(root_dir) for p in exclude_dirs]
    source_files = []
    for f in root_dir.rglob("*"):
        if f.is_file() and f.suffix in extensions:
            if any(excluded in f.parents for excluded in exclude_dirs):
                continue
            source_files.append(f)
    return source_files

def compute_relative_include(current_file: Path, include_path: str, project_root: Path):
    absolute_path = (project_root / include_path).resolve()
    if not absolute_path.exists():
        log(f"[MISSING] {include_path} in {current_file}", "error")
        MISSING_INCLUDES.append((current_file, include_path))
        return None
    try:
        return os.path.relpath(absolute_path, start=current_file.parent)
    except ValueError:
        log(f"[ERROR] Failed to compute relative path for {include_path} in {current_file}", "error")
        return None

def next_backup_filename(original: Path):
    i = 1
    while True:
        bak = original.with_suffix(original.suffix + f".bak{i}")
        if not bak.exists():
            return bak
        i += 1

def process_file(file_path: Path, project_root: Path, dry_run=False, force=False, make_backup=True, verbose=False, check_only=False, show_diff=False):
    try:
        lines = file_path.read_text(encoding='utf-8').splitlines(keepends=True)
    except Exception as e:
        log(f"[ERROR] Could not read file: {file_path} ({e})", "error")
        return False

    changed = False
    updated_lines = []

    for line in lines:
        match = INCLUDE_PATTERN.search(line)
        if match:
            subpath = match.group(1)
            rel_path = compute_relative_include(file_path, subpath, project_root)
            if rel_path:
                new_line = line.replace(f'"@/{subpath}"', f'"{rel_path}"')
                if new_line != line:
                    changed = True
                    log(f"[DEBUG] Updating include in {file_path.name}: {line.strip()} → {new_line.strip()}", "debug", verbose)
                    line = new_line
        updated_lines.append(line)

    if check_only:
        return changed

    if changed or force:
        if dry_run:
            log(f"[DRY-RUN] Would update: {file_path}", "update")
        else:
            if make_backup:
                backup_path = next_backup_filename(file_path)
                copyfile(file_path, backup_path)
                log(f"[BACKUP] Created: {backup_path}", "debug", verbose)
            try:
                if show_diff:
                    diff = unified_diff(
                        [l.rstrip('\n') for l in lines],
                        [l.rstrip('\n') for l in updated_lines],
                        fromfile=str(file_path),
                        tofile=str(file_path) + " (updated)",
                        lineterm=""
                    )
                    print("\n".join(diff))
                file_path.write_text("".join(updated_lines), encoding='utf-8')
                log(f"[UPDATED] {file_path}", "success")
            except Exception as e:
                log(f"[ERROR] Failed to write file: {file_path} ({e})", "error")
                return False
        return True
    else:
        log(f"[SKIPPED] {file_path}", "debug", verbose)
        return False

def main():
    parser = argparse.ArgumentParser(description="Fix #include \"@/...\" paths in C/C++ files.")
    parser.add_argument("root", nargs="?", default=".", help="Project root directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    parser.add_argument("--no-backup", action="store_true", help="Do not create .bak backup files")
    parser.add_argument("--force", action="store_true", help="Rewrite files even if not changed")
    parser.add_argument("--ext", nargs="*", help="Additional extensions to scan (e.g. cpp hpp)")
    parser.add_argument("--exclude", nargs="*", default=[], help="Folders to exclude (e.g. build third_party)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug output")
    parser.add_argument("--check-only", action="store_true", help="Only check for missing includes and possible changes")
    parser.add_argument("--show-diff", action="store_true", help="Show diff when changes are made")

    args = parser.parse_args()
    project_root = Path(args.root).resolve()

    if not project_root.exists():
        log(f"[ERROR] Root directory does not exist: {project_root}", "error")
        return

    extensions = set(DEFAULT_EXTENSIONS + tuple(f".{ext.lstrip('.')}" for ext in (args.ext or [])))
    exclude_dirs = args.exclude

    log(f"[INFO] Scanning {project_root} for extensions {extensions}", "info")
    files = find_source_files(project_root, extensions, exclude_dirs)

    total = len(files)
    updated = 0
    skipped = 0

    for f in files:
        result = process_file(
            f, project_root,
            dry_run=args.dry_run,
            force=args.force,
            make_backup=not args.no_backup,
            verbose=args.verbose,
            check_only=args.check_only,
            show_diff=args.show_diff
        )
        if result:
            updated += 1
        else:
            skipped += 1

    log(f"\nSummary:", "info")
    log(f"  Total files scanned     : {total}", "info")
    log(f"  Files updated           : {updated}", "success")
    log(f"  Files skipped           : {skipped}", "warn")
    log(f"  Missing include targets : {len(MISSING_INCLUDES)}", "error")
    if MISSING_INCLUDES:
        for file, include in MISSING_INCLUDES:
            log(f"    {file}: '@/ {include}' not found", "error")
    if args.dry_run:
        log("Dry-run mode: No files were written.", "warn")

if __name__ == "__main__":
    main()
