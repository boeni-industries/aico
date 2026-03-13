#!/usr/bin/env bash
set -euo pipefail

(
  cd gateway
  uv run python ../scripts/generate_openapi_public.py --check --output ../contracts/openapi/v1.json
  uv run python ../scripts/generate_openapi_internal.py --check --output ../contracts/openapi/internal-v1.json
  uv run python ../scripts/generate_websocket_contract.py --check --output ../contracts/websocket/v1.json
  uv run python ../scripts/generate_nats_contract.py --check --output ../contracts/nats/v1.json
)

if ! command -v buf >/dev/null 2>&1; then
  echo "buf is not installed. Install from https://buf.build/docs/installation or run via CI." >&2
  exit 1
fi

buf breaking --against contracts/proto
