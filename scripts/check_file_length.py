#!/usr/bin/env python3
"""
check_file_length.py — enforce a maximum line count per Python source file.

Rule: no Python file under src/ or tests/ may exceed MAX_LINES lines.

Why 150 lines?
  Small, focused files are easier to review, test, and reason about.
  150 lines is enough for one well-scoped class or a cohesive set of
  related functions — anything larger is a signal to split the module.

Usage:
    python scripts/check_file_length.py              # check src/ and tests/
    python scripts/check_file_length.py src/         # check a single tree
    python scripts/check_file_length.py --max 200    # override the limit
    python scripts/check_file_length.py --summary    # show all files, not just violations

Exit codes:
    0 — all files within the limit
    1 — one or more files exceed the limit
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MAX_LINES: int = 150
DEFAULT_ROOTS: list[str] = ["src", "tests"]


def count_lines(path: Path) -> int:
    """Return the number of lines in *path* (same as ``wc -l``)."""
    try:
        return path.read_text(encoding="utf-8", errors="replace").count("\n")
    except OSError:
        return 0


def collect_python_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
    return files


def check(
    roots: list[Path],
    max_lines: int = MAX_LINES,
    *,
    summary: bool = False,
) -> list[tuple[Path, int]]:
    """
    Check all Python files under *roots*.

    Returns a list of (path, line_count) for every file that exceeds *max_lines*.
    Also prints results to stdout.
    """
    violations: list[tuple[Path, int]] = []
    files = collect_python_files(roots)

    for path in files:
        n = count_lines(path)
        over = n > max_lines
        if over:
            violations.append((path, n))
        if summary or over:
            status = f"OVER ({n} > {max_lines})" if over else f"ok   ({n})"
            print(f"  {'✗' if over else '✓'}  {path}  — {status}")

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enforce a maximum line count per Python file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "roots",
        nargs="*",
        default=DEFAULT_ROOTS,
        help=f"Directories or files to check (default: {DEFAULT_ROOTS})",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=MAX_LINES,
        dest="max_lines",
        metavar="N",
        help=f"Maximum lines per file (default: {MAX_LINES})",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print all files, not just violations",
    )
    args = parser.parse_args(argv)

    roots = [Path(r) for r in args.roots]
    missing = [r for r in roots if not r.exists()]
    if missing:
        for m in missing:
            print(f"error: path not found: {m}", file=sys.stderr)
        return 2

    print(f"Checking Python files (max {args.max_lines} lines) …\n")
    violations = check(roots, max_lines=args.max_lines, summary=args.summary)

    print()
    if violations:
        print(f"❌  {len(violations)} file(s) exceed {args.max_lines} lines:")
        for path, n in violations:
            print(f"     {path}  ({n} lines)")
        print(
            f"\n   Split each file so that no single module exceeds {args.max_lines} lines."
        )
        return 1

    print(f"✅  All files are within the {args.max_lines}-line limit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
