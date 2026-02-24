# API Contract Freezing

This directory contains frozen API contracts for AICO's public interfaces.

## Structure

```
contracts/
├── openapi/
│   ├── v1.json          # Frozen OpenAPI 3.x spec for public /api/v1
│   └── internal-v1.json # Frozen OpenAPI 3.x spec for internal /api/v1 (admin/system/operations/users-sessions)
├── proto/
│   ├── *.proto          # Frozen protobuf baseline
│   └── buf.yaml         # Buf configuration for proto contracts
├── CHANGELOG.md         # Required: tracks all contract changes
└── README.md            # This file
```

## Policy: Strict but Practical

### ✅ Allowed (Non-Breaking Changes)
- **New endpoints** (REST)
- **New optional fields** (REST/Proto)
- **New enum values** with safe defaults
- **Documentation improvements**
- **Metadata corrections** that don't change contract shape

### ❌ Not Allowed in v1 (Breaking Changes)
- Removing or renaming endpoints/fields
- Changing field types
- Changing required ↔ optional semantics
- Tightening validation that rejects previously valid payloads
- **Action required**: Create `/api/v2` or version proto package

## How to Update Contracts

### 1. Make Your Code Changes
Implement your feature/bugfix in the codebase.

### 2. Contracts Auto-Regenerate on Commit
**Pre-commit hook automatically regenerates contracts** when you commit API changes:
- Detects changes to `backend/api/`, `proto/`, or `backend/api_gateway/`
- Auto-runs `scripts/generate_openapi_public.py`
- Auto-copies `proto/*.proto` to `contracts/proto/`
- Auto-stages the regenerated contracts

**Manual regeneration (optional):**
```bash
./scripts/regenerate_contracts.sh
```

### 3. Update CHANGELOG.md
Add an entry to `contracts/CHANGELOG.md` explaining:
- What changed (new endpoints, fields, etc.)
- Why (feature, bugfix, etc.)
- Compatibility impact (additive/non-breaking)

**The pre-commit hook will remind you if you forget.**

### 4. Commit
```bash
git add contracts/CHANGELOG.md  # if not already staged
git commit -m "feat(api): add new endpoint for X"
```

The pre-commit hook handles contract regeneration automatically.

### 5. CI Verification
CI will automatically verify:
- ✅ OpenAPI artifacts match generated specs
- ✅ Proto changes are backward-compatible (`buf breaking`)
- ✅ Proto passes linting (`buf lint`)
- ✅ CHANGELOG.md was updated

## CI Gates

Three workflows enforce contract stability:

1. **`openapi-contract.yml`**: Verifies OpenAPI artifact is up to date
   - public: `contracts/openapi/v1.json`
   - internal: `contracts/openapi/internal-v1.json`
2. **`proto-contract.yml`**: Runs `buf breaking` + `buf lint`
3. **`contract-policy.yml`**: Ensures CHANGELOG.md is updated when contracts change

All gates run on:
- Every pull request
- Every push to `main`/`master`

## Breaking Changes

If you need to make a breaking change:

1. **REST**: Create `/api/v2` endpoints
   - Keep `/api/v1` frozen and working
   - Implement new contract under `/api/v2`
   - Update `scripts/generate_openapi_public.py` to generate v2 spec

2. **Protobuf**: Version your proto package/service
   - Keep existing messages/fields stable
   - Create new versioned messages or packages
   - Update `buf.yaml` accordingly

3. **Document the migration path** in `contracts/CHANGELOG.md`

## Local Verification

**OpenAPI check:**
```bash
uv run python scripts/generate_openapi_public.py --check
```

**Protobuf check (requires Docker, optional):**
```bash
docker run --rm -v "$PWD":/work -w /work bufbuild/buf:latest lint
docker run --rm -v "$PWD":/work -w /work bufbuild/buf:latest breaking --against contracts/proto
```

**Or rely on CI** (recommended for multi-platform teams).

## Questions?

See `contracts/CHANGELOG.md` for the full policy and historical changes.
