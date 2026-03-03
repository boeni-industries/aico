# Contract Enforcement System

## Overview

AICO enforces API contract consistency through a multi-layered validation system that catches breaking changes early in the development cycle.

## Enforcement Layers

### 1. Pre-Commit Hook (Auto-Regeneration)
**Location:** `.git/hooks/pre-commit`

**Triggers:** When committing changes to API-related files (`backend/api/`, `proto/`, `backend/api_gateway/`)

**Actions:**
- Auto-regenerates OpenAPI contracts (`contracts/openapi/v1.json`, `contracts/openapi/internal-v1.json`)
- Copies proto files to contract baseline (`contracts/proto/`)
- Auto-stages regenerated contracts
- Reminds to update `contracts/CHANGELOG.md`

**Does NOT fail commits** - just ensures contracts stay in sync with code.

---

### 2. Pre-Push Hook (Validation)
**Location:** `.git/hooks/pre-push`

**Triggers:** Before pushing commits to remote repository

**Validations:**
1. **OpenAPI Public Contract** - Ensures generated spec matches committed artifact
2. **OpenAPI Internal Contract** - Validates internal API spec
3. **NATS Contract** - Checks NATS subject/message contracts
4. **Protobuf Breaking Changes** - Uses `buf breaking` to detect backwards-incompatible changes
5. **Protobuf Lint** - Ensures proto files follow style guidelines

**Fails push if any validation fails** - prevents broken contracts from reaching remote.

**Bypass (not recommended):**
```bash
git push --no-verify
```

---

### 3. GitHub Actions (CI/CD)
**Location:** `.github/workflows/`

**Triggers:** On all pushes and pull requests (updated to run on all branches)

**Workflows:**
- `openapi-contract.yml` - Validates OpenAPI specs are up to date
- `nats-contract.yml` - Validates NATS contract
- `proto-contract.yml` - Checks protobuf backwards compatibility and linting
- `websocket-contract.yml` - Validates WebSocket contract
- `contract-policy.yml` - Enforces CHANGELOG updates when contracts change

**Blocks merges if validation fails.**

---

## Contract Artifacts

All contract artifacts are stored in `contracts/`:

```
contracts/
├── CHANGELOG.md              # Required documentation of all contract changes
├── openapi/
│   ├── v1.json              # Public API contract
│   └── internal-v1.json     # Internal API contract
├── proto/                    # Protobuf contract baseline
│   └── *.proto
├── nats/
│   └── v1.json              # NATS subject/message contract
└── websocket/
    └── v1.json              # WebSocket event contract
```

---

## Development Workflow

### Making API Changes

1. **Modify API code** (`backend/api/`, `proto/`, etc.)
2. **Commit changes** - Pre-commit hook auto-regenerates contracts
3. **Update CHANGELOG** - Add entry to `contracts/CHANGELOG.md`:
   ```markdown
   ## [Unreleased]
   ### Added
   - New endpoint: `POST /api/v1/example` - Description of what it does
   
   ### Changed
   - Modified `GET /api/v1/users` response schema - Added `nickname` field (additive, non-breaking)
   
   ### Breaking
   - Removed deprecated `GET /api/v1/old-endpoint`
   ```
4. **Stage CHANGELOG** - `git add contracts/CHANGELOG.md`
5. **Push changes** - Pre-push hook validates contracts
6. **GitHub Actions** - CI validates on remote

---

## Contract Validation Commands

### Manual Validation (Local)

```bash
# Check all contracts
uv run python scripts/generate_openapi_public.py --check
uv run python scripts/generate_openapi_internal.py --check
uv run python scripts/generate_nats_contract.py --check
buf breaking --against contracts/proto
buf lint
```

### Regenerate Contracts

```bash
# Regenerate OpenAPI contracts
uv run python scripts/generate_openapi_public.py
uv run python scripts/generate_openapi_internal.py

# Regenerate NATS contract
uv run python scripts/generate_nats_contract.py

# Update proto baseline
cp -f proto/*.proto contracts/proto/
```

---

## Breaking Changes Policy

### What Constitutes a Breaking Change?

**OpenAPI/REST:**
- Removing endpoints
- Removing request/response fields
- Changing field types
- Making optional fields required
- Changing HTTP methods

**Protobuf:**
- Removing fields
- Changing field types
- Changing field numbers
- Renaming fields (without field number preservation)

**NATS:**
- Changing subject patterns
- Removing message types
- Changing message schemas (non-additive)

### Handling Breaking Changes

1. **Document in CHANGELOG** - Clearly mark as `### Breaking`
2. **Version bump** - Consider API versioning (`/api/v2/`)
3. **Deprecation period** - Maintain old endpoint alongside new one
4. **Migration guide** - Document how clients should migrate

---

## Troubleshooting

### Pre-Push Hook Fails

**Error:** "OpenAPI contract out of sync"
```bash
# Fix: Regenerate the contract
uv run python scripts/generate_openapi_public.py
git add contracts/openapi/v1.json
git commit --amend --no-edit
```

**Error:** "Breaking protobuf changes detected"
```bash
# Review changes
buf breaking --against contracts/proto

# If intentional, update baseline
cp -f proto/*.proto contracts/proto/
git add contracts/proto/
git commit -m "chore: update proto baseline for breaking changes"
```

### GitHub Actions Fail

Check the workflow run logs in GitHub Actions tab. Common issues:
- Forgot to commit regenerated contracts
- Forgot to update `contracts/CHANGELOG.md`
- Introduced breaking changes without versioning

---

## Recent Updates (March 2026)

**Enhanced Enforcement:**
- ✅ Added pre-push hook for local validation before remote push
- ✅ Updated GitHub workflows to run on **all pushes**, not just main/master
- ✅ Catches contract violations earlier in development cycle

**Why the Change:**
Previously, contract validation only ran on PRs and pushes to main/master. This allowed breaking changes to accumulate on feature branches. The new system validates on every push, catching issues immediately.

---

## Best Practices

1. **Run validation locally** before pushing (pre-push hook does this automatically)
2. **Update CHANGELOG** with every contract change
3. **Use additive changes** when possible (add fields, don't remove)
4. **Version breaking changes** - Use `/api/v2/` for incompatible changes
5. **Test contract generation** - Ensure scripts run successfully in CI environment
6. **Review contract diffs** - Check `git diff contracts/` before committing

---

## Related Documentation

- [API Versioning Strategy](./api-versioning.md)
- [Protobuf Style Guide](./protobuf-style.md)
- [NATS Subject Naming](./nats-subjects.md)
