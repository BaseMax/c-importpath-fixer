#!/usr/bin/env python3
"""
c-importpath-fixer: Fixes #include "@/..." directives in C/C++ source files
by replacing them with correct relative paths from the file to the project root.

Author: github.com/BaseMax
License: MIT
"""

import os
import re
import argparse

INCLUDE_PATTERN = re.compile(r'#include\s+"@/(.+?)"')

def find_source_files(root_dir):
    """Recursively find all .c and .h files under the given directory."""
    source_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(('.c', '.h')):
                source_files.append(os.path.join(dirpath, filename))
    return source_files

def fix_include_paths(file_path, project_root):
    """Fix @/ include paths in a single file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    file_dir = os.path.dirname(file_path)
    changed = False
    updated_lines = []

    for line in lines:
        match = INCLUDE_PATTERN.search(line)
        if match:
            include_subpath = match.group(1)
            absolute_include_path = os.path.normpath(os.path.join(project_root, include_subpath))
            try:
                relative_path = os.path.relpath(absolute_include_path, start=file_dir)
                new_line = line.replace(f'"@/{include_subpath}"', f'"{relative_path}"')
                updated_lines.append(new_line)
                changed = True
            except ValueError:
                print(f"[WARN] Failed to compute relative path for {include_subpath} in {file_path}")
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        print(f"[UPDATED] {file_path}")

def main():
    parser = argparse.ArgumentParser(description="Fix @/ include paths in C/C++ source files.")
    parser.add_argument(
        "root", nargs="?", default=".", help="Project root directory (default: current directory)"
    )
    args = parser.parse_args()

    project_root = os.path.abspath(args.root)
    source_files = find_source_files(project_root)

    if not source_files:
        print("No .c or .h files found.")
        return

    for file_path in source_files:
        fix_include_paths(file_path, project_root)

    print("Done fixing include paths.")

if __name__ == "__main__":
    main()
