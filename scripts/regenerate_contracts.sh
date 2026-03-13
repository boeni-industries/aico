#!/usr/bin/env bash
set -e

# AICO Contract Regeneration Script
# Run this manually when you've changed API code and want to update contracts

echo "🔄 Regenerating API contracts..."

pushd gateway >/dev/null

# Regenerate OpenAPI contract
echo "  → Regenerating OpenAPI contract..."
uv run python ../scripts/generate_openapi_public.py --output ../contracts/openapi/v1.json

echo "  → Regenerating internal OpenAPI contract..."
uv run python ../scripts/generate_openapi_internal.py --output ../contracts/openapi/internal-v1.json

echo "  → Regenerating WebSocket contract..."
uv run python ../scripts/generate_websocket_contract.py --output ../contracts/websocket/v1.json

echo "  → Regenerating NATS contract..."
uv run python ../scripts/generate_nats_contract.py --output ../contracts/nats/v1.json

popd >/dev/null

# Regenerate Proto contract baseline
echo "  → Updating proto baseline..."
cp -f proto/*.proto contracts/proto/

echo ""
echo "✅ Contracts regenerated successfully"
echo ""
echo "Next steps:"
echo "  1. Update contracts/CHANGELOG.md with your changes"
echo "  2. Stage and commit: git add contracts/ && git commit"
echo ""
