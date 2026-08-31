#!/usr/bin/env python3
"""
Fully uninstall OpenRAG from the local development environment.

Removes by default:
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

With --with-docker also stops and removes:
  - All OpenRAG docker-compose services, networks, and volumes
    (matches the `make clean` behavior — equivalent to
     `docker compose down -v --remove-orphans` plus image pruning)

Does NOT remove:
  - .env file (user configuration)
  - Pre-existing OpenSearch data directory outside the compose volume

Examples:
  python3 scripts/uninstall.py --dry-run
  python3 scripts/uninstall.py --with-docker
  python3 scripts/uninstall.py --with-docker --force
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
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

DOCKER_IMAGE_PREFIXES = (
    "langflowai/openrag",
    "langflow/langflow",
    "opensearchproject/opensearch",
)


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


def _format_size(path: Path) -> str:
    """Return a human-readable size string, or empty if unavailable."""
    if path.name in (".venv", "site-packages"):
        return "(size skipped)"
    if path.is_file():
        return f"({path.stat().st_size / 1024:.1f} KB)"
    if path.is_dir():
        size = sum(
            f.stat().st_size for f in path.rglob("*") if f.is_file()
        )
        return f"({size / (1024 * 1024):.1f} MB)"
    return ""


def _remove(targets: list[tuple[str, Path]], *, dry_run: bool) -> int:
    removed = 0
    for label, path in targets:
        size_str = _format_size(path)
        if path.is_dir():
            if dry_run:
                print(f"  [dry-run] would remove directory: {path} {size_str}")
            else:
                shutil.rmtree(path)
                print(f"  removed: {path} {size_str}")
        elif path.is_file():
            if dry_run:
                print(f"  [dry-run] would remove file: {path} {size_str}")
            else:
                path.unlink()
                print(f"  removed: {path} {size_str}")
        removed += 1
    return removed


def _check_docker() -> list[str] | None:
    """Return the argv prefix for docker compose if the daemon is running."""
    for runtime in ("docker", "podman"):
        if not shutil.which(runtime):
            continue
        r = subprocess.run(
            [runtime, "info"], capture_output=True, timeout=5, check=False,
        )
        if r.returncode == 0:
            return [runtime, "compose"]
    return None


def _run(cmd: list[str], *, cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a command with a timeout, returning the CompletedProcess."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                         timeout=timeout, check=False)


def _cleanup_docker(*, dry_run: bool, force: bool) -> int:
    """Stop and remove OpenRAG docker-compose stacks, networks, volumes, images."""
    actions = 0
    runtime_prefix = _check_docker()
    if runtime_prefix is None:
        print("  [skip] no running docker/podman daemon found")
        return actions

    if not (TOP / "docker-compose.yml").exists():
        print("  [skip] docker-compose.yml not found at repo root")
        return actions

    cmd_down = [*runtime_prefix, "down", "-v", "--remove-orphans"]
    if dry_run:
        print(f"  [dry-run] would run: {' '.join(cmd_down)}")
    else:
        print(f"  running: {' '.join(cmd_down)}")
        try:
            result = _run(cmd_down, cwd=TOP, timeout=120)
            if result.returncode != 0:
                print(f"  [warn] compose down exited with code {result.returncode}")
        except subprocess.TimeoutExpired:
            print("  [warn] compose down timed out after 120s")
    actions += 1

    for override in (
        TOP / "docker-compose.dev.yml",
        TOP / "docker-compose.gpu.yml",
        TOP / "docker-compose.backend-port.yml",
        TOP / "docker-compose.host-backend.yml",
    ):
        if not override.exists():
            continue
        cmd = [*runtime_prefix, "-f", "docker-compose.yml",
               "-f", override.name, "down", "-v", "--remove-orphans"]
        if dry_run:
            print(f"  [dry-run] would run: {' '.join(cmd)}")
        else:
            print(f"  running: {' '.join(cmd)}")
            try:
                _run(cmd, cwd=TOP, timeout=120)
            except subprocess.TimeoutExpired:
                print(f"  [warn] compose down ({override.name}) timed out")
        actions += 1

    cmd_rmi = [*runtime_prefix, "image", "prune", "-f"]
    if dry_run:
        print(f"  [dry-run] would run: {' '.join(cmd_rmi)}")
    else:
        print(f"  running: {' '.join(cmd_rmi)}")
        try:
            _run(cmd_rmi, cwd=TOP, timeout=60)
        except subprocess.TimeoutExpired:
            print("  [warn] image prune timed out")
    actions += 1

    if force:
        cmd_rm = [*runtime_prefix, "images", "--format",
                  "{{.Repository}}:{{.Tag}} {{.ID}}"]
        out = None
        try:
            out = _run(cmd_rm, cwd=TOP, timeout=15)
        except subprocess.TimeoutExpired:
            print("  [warn] docker images listing timed out")
        if out and out.returncode == 0:
            for line in out.stdout.splitlines():
                repo_id = line.split()
                if not repo_id:
                    continue
                repo = repo_id[0]
                if any(repo.startswith(p) for p in DOCKER_IMAGE_PREFIXES):
                    cmd = [*runtime_prefix, "image", "rm", "-f", repo_id[1]]
                    if dry_run:
                        print(f"  [dry-run] would run: {' '.join(cmd)}")
                    else:
                        print(f"  running: {' '.join(cmd)}")
                        try:
                            _run(cmd, cwd=TOP, timeout=60)
                        except subprocess.TimeoutExpired:
                            print(f"  [warn] image rm {repo_id[1]} timed out")
                    actions += 1
    return actions


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
        help="Skip the confirmation prompt; with --with-docker also remove OpenRAG images",
    )
    parser.add_argument(
        "--with-docker", action="store_true",
        help="Also stop and remove Docker containers, networks, and volumes",
    )
    args = parser.parse_args()

    targets = _collect_targets(PATTERNS)
    has_docker_work = args.with_docker and _check_docker() is not None

    if not targets and not has_docker_work:
        print("Nothing to remove — no installation artifacts found.")
        return 0

    print("The following artifacts will be removed:")
    for label, path in targets:
        print(f"  {label}  {_format_size(path)}")

    if has_docker_work:
        print("\nThe following Docker resources will be removed:")
        print("  - OpenRAG compose stacks (volumes + orphans)")
        print("  - Dangling docker images")
        if args.force:
            print("  - OpenRAG-prefixed docker images (langflowai/openrag*, "
                  "langflow/langflow, opensearchproject/opensearch*)")

    if not args.force and not args.dry_run:
        confirm = input("\nProceed with removal? [y/N] ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    print()
    file_count = _remove(targets, dry_run=args.dry_run)
    docker_actions = 0
    if has_docker_work:
        docker_actions = _cleanup_docker(
            dry_run=args.dry_run, force=args.force,
        )

    print()
    if args.dry_run:
        print(f"Dry run complete — {file_count} file/dir item(s) and "
              f"{docker_actions} docker action(s) would be performed.")
    else:
        print(f"Done. Removed {file_count} file/dir item(s), "
              f"ran {docker_actions} docker action(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())