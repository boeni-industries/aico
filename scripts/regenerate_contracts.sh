#!/usr/bin/env bash
set -e

# AICO Contract Regeneration Script
# Run this manually when you've changed API code and want to update contracts

echo "🔄 Regenerating API contracts..."

# Regenerate OpenAPI contract
echo "  → Regenerating OpenAPI contract..."
uv run python scripts/generate_openapi_public.py

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
