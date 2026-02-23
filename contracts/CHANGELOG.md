# API Contract Changelog

This file tracks all changes to the frozen API contracts in `/contracts/`.

## Policy

### Allowed Changes (Non-Breaking)
- **Additive changes only**: new endpoints, new optional fields, new enum values
- **Bugfixes**: metadata corrections that don't change contract shape
- **Documentation**: improved descriptions, examples

### Breaking Changes (Require Version Bump)
- Removing or renaming endpoints/fields
- Changing field types or required/optional semantics
- Tightening validation that rejects previously valid payloads
- **Action required**: Create `/api/v2` (REST) or version proto package/service

### Update Workflow
1. Make your code changes
2. Regenerate contracts:
   - REST: `uv run python scripts/generate_openapi_public.py`
   - Proto: `cp -f proto/*.proto contracts/proto/`
3. Add entry to this CHANGELOG with rationale
4. Commit all changes together
5. CI will verify:
   - OpenAPI artifact matches generated spec
   - Proto changes are backward-compatible (buf breaking)
   - CHANGELOG was updated

---

## [Unreleased]

### 2026-02-24 - Initial Contract Freeze
- **OpenAPI v1**: Frozen `/api/v1` REST contract at `contracts/openapi/v1.json`
- **Protobuf**: Frozen proto baseline at `contracts/proto/*.proto`
- **CI Gates**: Added strict breaking change detection for both REST and Protobuf
- **Policy**: Established Option 2 (strict but practical) - additive changes allowed via explicit contract update PR, breaking changes require version bump
