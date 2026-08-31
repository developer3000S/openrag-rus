fuser -k 5001/tcp 2>/dev/null || true

uv run python scripts/docling_ctl.py start --port 5001

uv run python scripts/docling_ctl.py status
