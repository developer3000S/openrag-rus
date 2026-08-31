#!/usr/bin/env python3
"""
Fully uninstall OpenRAG from the local development environment.

Removes:
  - .venv/                          Python virtual environment
  - src/openrag.egg-info/           Package install metadata
  - src/__pycache__/                Compiled bytecode (root level)
  - src/**/__pycache__/             Compiled bytecode (all subdirectories)
  - .pytest_cache/                  pytest cache
  - .ruff_cache/                    ruff linter cache
  - .mypy_cache/                    mypy cache
  - build/, dist/                   Python build artifacts
  - sdks/python/__pycache__/        SDK bytecode
  - sdks/mcp/__pycache__/           MCP SDK bytecode
  - sdks/python/src/**/__pycache__/ SDK nested bytecode

Does NOT remove:
  - Docker containers/volumes (use `make clean` for that)
  - .env file (user configuration)
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


TOP = Path(__file__).resolve().parents[1]
PATTERNS: list[tuple[str, Path | None]] = [
    (".venv", TOP / ".venv"),
    ("src/openrag.egg-info/", TOP / "src" / "openrag.egg-info"),
    ("src/__pycache__/", TOP / "src" / "__pycache__"),
    ("src/**/__pycache__/", TOP / "src"),
    (".pytest_cache/", TOP / ".pytest_cache"),
    (".ruff_cache/", TOP / ".ruff_cache"),
    (".mypy_cache/", TOP / ".mypy_cache"),
    ("build/", TOP / "build"),
    ("dist/", TOP / "dist"),
    ("sdks/python/__pycache__/", TOP / "sdks" / "python" / "__pycache__"),
    ("sdks/python/src/__pycache__/", TOP / "sdks" / "python" / "src"),
    ("sdks/mcp/__pycache__/", TOP / "sdks" / "mcp" / "__pycache__"),
]


def _collect_targets(patterns: list[tuple[str, Path | None]]) -> list[tuple[str, Path]]:
    """Return explicit (label, path) pairs for existing directories/files."""
    targets: list[tuple[str, Path]] = []
    for label, base in patterns:
        if base is None:
            continue
        if "**/__pycache__" in label:
            for nested in base.rglob("__pycache__"):
                if nested.is_dir():
                    targets.append((f"{nested.relative_to(TOP)}/", nested))
        else:
            targets.append((label, base))
    return [(l, p) for l, p in targets if p.exists()]


def _remove(targets: list[tuple[str, Path]], *, dry_run: bool) -> int:
    removed = 0
    for label, path in targets:
        if path.is_dir():
            if path.name in (".venv", "site-packages"):
                size_mb = -1.0
                size_str = "(size skipped)"
            else:
                size = sum(
                    f.stat().st_size
                    for f in path.rglob("*") if f.is_file()
                )
                size_mb = size / (1024 * 1024)
                size_str = f"({size_mb:.1f} MB)"
            if dry_run:
                print(f"  [dry-run] would remove directory: {path} {size_str}")
            else:
                shutil.rmtree(path)
                print(f"  removed: {path} {size_str}")
        elif path.is_file():
            size_kb = path.stat().st_size / 1024
            if dry_run:
                print(f"  [dry-run] would remove file: {path} ({size_kb:.1f} KB)")
            else:
                path.unlink()
                print(f"  removed: {path} ({size_kb:.1f} KB)")
        removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true",
        help="Show what would be removed without actually removing anything",
    )
    parser.add_argument(
        "--force", "-f", action="store_true",
        help="Skip the confirmation prompt",
    )
    args = parser.parse_args()

    targets = _collect_targets(PATTERNS)
    if not targets:
        print("Nothing to remove — no installation artifacts found.")
        return 0

    print("The following artifacts will be removed:")
    for label, path in targets:
        if path.is_dir() and path.name in (".venv", "site-packages"):
            size_str = "(size skipped)"
        elif path.is_dir():
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            size_str = f"({size / (1024 * 1024):.1f} MB)"
        else:
            size_str = f"({path.stat().st_size / 1024:.1f} KB)"
        print(f"  {label}  {size_str}")

    if not args.force:
        confirm = input("\nProceed with removal? [y/N] ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    print()
    count = _remove(targets, dry_run=args.dry_run)
    print()
    if args.dry_run:
        print(f"Dry run complete — {count} item(s) would be removed.")
    else:
        print(f"Done. Removed {count} item(s).")
        print("To also stop and remove Docker containers/volumes, run: make clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
