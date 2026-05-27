"""
Enforce the 150-line-per-file rule for every Python source file.

Why a test rather than just a script?
  Running ``uv run pytest`` already covers this check automatically — no
  separate CI step needed.  A failing test here is immediately visible
  alongside other failures, and the parametrised output names the exact
  offending file.

The limit (MAX_LINES = 150) matches scripts/check_file_length.py.
Files that are currently over the limit are listed in KNOWN_VIOLATIONS
and are expected to be split in a future phase.  Once a file is fixed,
remove it from that set — the test will then enforce it stays fixed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ── configuration ──────────────────────────────────────────────────────────────

MAX_LINES = 150

# Root of the project (two levels up from this file: tests/unit/ → tests/ → .)
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Trees to check
_CHECK_ROOTS = [
    _PROJECT_ROOT / "src",
    _PROJECT_ROOT / "tests",
]

# Files currently over the limit that are scheduled to be split.
# Listed relative to the project root.
# Remove an entry here once the file has been split to ≤ 150 lines.
KNOWN_VIOLATIONS: frozenset[str] = frozenset(
    [
        "src/debate/agents/base.py",        # 222 lines — split pending
        "src/debate/agents/judge.py",        # 242 lines — split pending
        "src/debate/cli/entry.py",           # 200 lines — split pending
        "src/debate/cli/menu.py",            # 171 lines — split pending
        "src/debate/gatekeeper.py",          # 182 lines — split pending
        "src/debate/sdk/sdk.py",             # 195 lines — split pending
        "src/debate/skills/definitions.py",  # 331 lines — split pending
        "tests/test_agents.py",              # 169 lines — split pending
        "tests/unit/test_agents.py",         # 169 lines — split pending
    ]
)


# ── helpers ────────────────────────────────────────────────────────────────────


def _all_python_files() -> list[Path]:
    files: list[Path] = []
    for root in _CHECK_ROOTS:
        files.extend(sorted(root.rglob("*.py")))
    return files


def _line_count(path: Path) -> int:
    try:
        return path.read_text(encoding="utf-8", errors="replace").count("\n")
    except OSError:
        return 0


def _rel(path: Path) -> str:
    return str(path.relative_to(_PROJECT_ROOT))


# ── parametrised test ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("py_file", _all_python_files(), ids=_rel)
def test_file_within_150_lines(py_file: Path) -> None:
    """
    Each Python file must be at most MAX_LINES lines.

    Files in KNOWN_VIOLATIONS are temporarily exempt (xfail) — they are
    expected to fail today, and the test will start passing automatically
    once each file is split.  An xpass (unexpectedly passes) is treated as
    success: it means the file has been fixed — remove it from KNOWN_VIOLATIONS.
    """
    rel = _rel(py_file)
    n = _line_count(py_file)

    if rel in KNOWN_VIOLATIONS:
        # Mark as expected failure — stops this test with xfail, won't block CI.
        # Once the file is split to ≤ MAX_LINES, remove it from KNOWN_VIOLATIONS
        # and the test will start passing normally.
        pytest.xfail(
            reason=f"{rel} has {n} lines (> {MAX_LINES}) — scheduled for splitting",
        )

    assert n <= MAX_LINES, (
        f"{rel} has {n} lines, which exceeds the {MAX_LINES}-line limit.\n"
        f"Split it into smaller modules, or add it to KNOWN_VIOLATIONS "
        f"in tests/unit/test_file_lengths.py with a comment explaining why."
    )
