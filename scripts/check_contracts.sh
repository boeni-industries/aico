#!/usr/bin/env bash
set -euo pipefail

uv run python scripts/generate_openapi_public.py --check
uv run python scripts/generate_openapi_internal.py --check
uv run python scripts/generate_websocket_contract.py --check

if ! command -v buf >/dev/null 2>&1; then
  echo "buf is not installed. Install from https://buf.build/docs/installation or run via CI." >&2
  exit 1
fi

buf breaking --against contracts/proto
