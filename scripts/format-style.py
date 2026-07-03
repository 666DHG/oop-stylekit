#!/usr/bin/env python3
"""Run clang-format, then apply course-specific formatting fixes."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path.cwd().resolve()
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx"}
SKIP_DIRS = {".git", ".build", "build", "out", "__pycache__"}
DEFAULT_SKIP_DIRS = SKIP_DIRS | {"example"}


def iter_source_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    explicit_targets = bool(targets)
    pending = targets or [ROOT]

    for target in pending:
        if target.is_file():
            candidates = [target]
        elif target.is_dir():
            candidates = target.rglob("*")
        else:
            print(f"warning: target does not exist: {target}", file=sys.stderr)
            continue

        for path in candidates:
            if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
                continue
            try:
                parts = path.resolve().relative_to(ROOT).parts
            except ValueError:
                parts = path.resolve().parts
            skip_dirs = SKIP_DIRS if explicit_targets else DEFAULT_SKIP_DIRS
            if any(part in skip_dirs for part in parts):
                continue
            files.append(path.resolve())

    return sorted(set(files))


def read_text(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace"), "utf-8"


def is_default_label_start(stripped: str) -> bool:
    return stripped == "default" or (
        stripped.startswith("default")
        and len(stripped) > len("default")
        and stripped[len("default")] in {":", " ", "\t", "/"}
    )


def find_label_colon(line: str, in_block_comment: bool) -> tuple[int | None, bool]:
    stripped = line.lstrip()
    indent_len = len(line) - len(stripped)
    if stripped.startswith("case "):
        scan_from = indent_len + len("case ")
    elif is_default_label_start(stripped):
        scan_from = indent_len + len("default")
    else:
        scan_from = len(line)

    in_string = False
    in_char = False
    escaped = False
    ternary_depth = 0
    index = 0
    label_colon: int | None = None

    while index < len(line):
        char = line[index]
        nxt = line[index:index + 2]

        if in_block_comment:
            if nxt == "*/":
                in_block_comment = False
                index += 2
                continue
            index += 1
            continue

        if escaped:
            escaped = False
            index += 1
            continue

        if char == "\\" and (in_string or in_char):
            escaped = True
            index += 1
            continue

        if not in_string and not in_char:
            if nxt == "//":
                break
            if nxt == "/*":
                in_block_comment = True
                index += 2
                continue

        if char == '"' and not in_char:
            in_string = not in_string
        elif char == "'" and not in_string:
            in_char = not in_char
        elif index >= scan_from and not in_string and not in_char:
            if char == "?":
                ternary_depth += 1
            elif char == ":":
                if line[index - 1:index + 1] == "::" or line[index:index + 2] == "::":
                    index += 1
                    continue
                if ternary_depth > 0:
                    ternary_depth -= 1
                else:
                    label_colon = index
                    break

        index += 1

    return label_colon, in_block_comment


def fix_case_default_colons(text: str) -> str:
    lines = text.splitlines(keepends=True)
    fixed_lines: list[str] = []
    in_block_comment = False

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        newline = raw_line[len(line):]
        stripped = line.lstrip()
        label_colon, in_block_comment = find_label_colon(line, in_block_comment)

        if label_colon is not None and (stripped.startswith("case ") or is_default_label_start(stripped)):
            before = line[:label_colon].rstrip()
            after = line[label_colon + 1:].lstrip()
            line = f"{before} : {after}"

        fixed_lines.append(line + newline)

    return "".join(fixed_lines)


def run_clang_format(files: list[Path], clang_format: str) -> None:
    for path in files:
        subprocess.run([clang_format, "-i", str(path)], check=True)


def postprocess_files(files: list[Path]) -> int:
    changed = 0
    for path in files:
        original, encoding = read_text(path)
        formatted = fix_case_default_colons(original)
        if formatted != original:
            path.write_text(formatted, encoding=encoding, newline="")
            changed += 1
    return changed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Format C/C++ files with clang-format and course-specific fixes."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        type=Path,
        help="Files or directories to format. Defaults to the repository root.",
    )
    parser.add_argument(
        "--clang-format",
        default="clang-format",
        help="clang-format executable name or path.",
    )
    parser.add_argument(
        "--postprocess-only",
        action="store_true",
        help="Skip clang-format and only fix course-specific spacing.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print errors. Useful when running from editor save hooks.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    files = iter_source_files([target.resolve() for target in args.targets])
    if not files:
        if not args.quiet:
            print("No C/C++ source files found.")
        return 0

    if not args.postprocess_only:
        clang_format = shutil.which(args.clang_format) or args.clang_format
        try:
            run_clang_format(files, clang_format)
        except FileNotFoundError:
            print("error: clang-format was not found. Install LLVM or add clang-format to PATH.", file=sys.stderr)
            return 1
        except subprocess.CalledProcessError as error:
            return error.returncode

    changed = postprocess_files(files)
    if not args.quiet:
        print(f"Formatted {len(files)} file(s); adjusted case/default labels in {changed} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
