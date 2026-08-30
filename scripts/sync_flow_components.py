#!/usr/bin/env python3
"""
Sync component code from the running Langflow container into local flow JSON files.

Extracts the current source of ChatInput, Agent, and MCPToolsComponent from the
running openrag-langflow container, computes the correct code_hash, and updates
every flow in ./flows/ so Langflow no longer reports "outdated components".

Usage:
    python scripts/sync_flow_components.py
    python scripts/sync_flow_components.py --container openrag-langflow --flows-dir flows
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
FLOWS_DIR = ROOT / "flows"


def _code_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]


def _run_docker_exec(container: str, cmd: list[str]) -> str:
    result = subprocess.run(
        ["docker", "exec", container] + cmd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _fetch_source(container: str, path_in_container: str) -> str:
    """Fetch a Python source file from inside the container."""
    return _run_docker_exec(container, ["cat", path_in_container])


COMPONENTS = [
    {
        "name": "Chat Input",
        "display_name": "Chat Input",
        "module": "custom_components.chat_input",
        "container_path": "/usr/local/lib/python3.14/site-packages/lfx/components/input_output/chat.py",
    },
    {
        "name": "Agent",
        "display_name": "Agent",
        "module": "custom_components.agent",
        "container_path": "/usr/local/lib/python3.14/site-packages/lfx/components/models_and_agents/agent.py",
    },
    {
        "name": "MCP Tools",
        "display_name": "MCP Tools",
        "module": "custom_components.mcp_tools",
        "container_path": "/usr/local/lib/python3.14/site-packages/lfx/components/models_and_agents/mcp_component.py",
    },
]


def update_flow(
    flow_path: Path,
    code: str,
    *,
    display_name: str,
    module: str,
    dry_run: bool,
) -> bool:
    """Update embedded code + code_hash for a named component in a flow JSON."""
    with flow_path.open(encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            print(f"  [skip] failed to parse {flow_path}: {exc}", file=__import__("sys").stderr)
            return False

    expected_hash = _code_hash(code)
    changed = False

    for node in data.get("data", {}).get("nodes", []):
        node_data = node.get("data", {})
        component = node_data.get("node", {})

        if component.get("display_name") != display_name:
            continue

        template = component.get("template", {})
        if not isinstance(template, dict):
            continue

        code_entry = template.get("code", {})
        if not isinstance(code_entry, dict) or "value" not in code_entry:
            continue

        current_code = code_entry.get("value", "")
        current_hash = component.get("metadata", {}).get("code_hash", "")

        if current_code == code and current_hash == expected_hash:
            continue  # already up to date

        if not dry_run:
            template["code"]["value"] = code
            component.setdefault("metadata", {})["code_hash"] = expected_hash

        changed = True

    if changed and not dry_run:
        flow_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return changed


def _fetch_from_index(container: str, display_name: str) -> Optional[str]:
    """Fetch the current source code for a component by name from the container's
    in-memory component cache (fastest, always correct)."""
    # Read the Langflow's own /app/flows/component_index.json (volume-backed)
    # for the trusted code. That file is the same data the server uses to
    # decide outdated vs. up-to-date.
    try:
        result = subprocess.run(
            ["docker", "exec", container, "cat", "/app/flows/component_index.json"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        return None

    try:
        d = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    for _, comps in d.get("entries", []):
        if not isinstance(comps, dict):
            continue
        data = comps.get(display_name)
        if isinstance(data, dict):
            code = data.get("template", {}).get("code", {}).get("value", "")
            if code:
                return code
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync component code from Langflow container into flow files.")
    parser.add_argument("--container", default="openrag-langflow", help="Docker container name")
    parser.add_argument("--flows-dir", type=Path, default=FLOWS_DIR, help="Flows directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without modifying files")
    args = parser.parse_args()

    if not args.flows_dir.exists():
        raise SystemExit(f"[error] flows directory not found: {args.flows_dir}")

    print(f"Fetching component sources from container '{args.container}' (via in-memory cache)...")

    # Fetch all sources first — prefer in-memory cache (always correct), fall back to .py file
    sources: dict[str, str] = {}
    for comp in COMPONENTS:
        # Fast path: ask Langflow's component cache directly
        code = _fetch_from_index(args.container, comp["name"])
        if code:
            sources[comp["name"]] = code
            h = _code_hash(code)
            print(f"  {comp['name']}: hash={h} (from cache) len={len(code)}")
            continue

        # Fallback: read .py source from container filesystem
        try:
            src = _fetch_source(args.container, comp["container_path"])
            sources[comp["name"]] = src
            h = _code_hash(src)
            print(f"  {comp['name']}: hash={h} (from .py file) len={len(src)}")
        except subprocess.CalledProcessError as exc:
            print(f"  [error] failed to fetch {comp['name']}: {exc.stderr}", file=__import__("sys").stderr)
            continue

    if not sources:
        raise SystemExit("[error] no component sources fetched — aborting")

    # Collect flow files
    flow_files = [
        p for p in sorted(args.flows_dir.glob("*.json"))
        if p.name != "component_index.json"
    ]
    print(f"\nUpdating {len(flow_files)} flow file(s)...\n")

    total_changes = 0
    for flow_path in flow_files:
        changes_in_file = []
        for comp in COMPONENTS:
            if comp["name"] not in sources:
                continue
            changed = update_flow(
                flow_path,
                sources[comp["name"]],
                display_name=comp["display_name"],
                module=comp["module"],
                dry_run=args.dry_run,
            )
            if changed:
                changes_in_file.append(comp["name"])

        if changes_in_file:
            status = "DRY-RUN" if args.dry_run else "UPDATED"
            print(f"  [{status}] {flow_path.name}: {', '.join(changes_in_file)}")
            total_changes += len(changes_in_file)
        elif not args.dry_run:
            print(f"  [ok]     {flow_path.name}: no change needed")

    print(f"\nDone. {total_changes} component(s) {'would be' if args.dry_run else 'were'} updated.")


if __name__ == "__main__":
    main()
