# WIP: Studio Multi-Tenancy

## Goal
Implement multi-tenancy in **AICO Studio** in a way that maximizes UX, guarantees tenant isolation (no cross-tenant bleeding), and stays maintainable.

## Key Principles
- **Tenant isolation is token-derived**: the backend must scope by `tenant_id` from the JWT (Studio must not “pick tenant” via `X-Tenant-ID` headers or query params).
- **Tenant switching is explicit and safe**: switching tenants must hard-reset all tenant-scoped client state.
- **Everything tenant-scoped is partitioned**: browser storage, caches, encryption sessions, and refresh flows must be keyed by `deployment + tenant`.

## Concrete Recommendations (Studio / `aico-studio`)
- **Make “Deployment” and “Tenant” first-class UI state**
  - **Deployment**: which gateway endpoint you’re managing (our cloud / enterprise on-prem / enterprise cloud).
  - **Tenant**: which tenant inside that deployment.
  - Provide a persistent top-bar selector that always shows the active `deployment / tenant`.

- **Introduce a `TenantContext` next to the existing `AuthContext`**
  - Keep `AuthContext` focused on authentication state.
  - Add `TenantContext` with:
    - `deploymentId`, `apiBaseUrl`
    - `tenantId`, `tenantDisplayName`
    - `setActiveTenant(...)` that triggers a hard reset (below).

- **Partition all client-side persistence by `deploymentId + tenantId`**
  - Today `src/api/config.ts` stores tokens/profile under global keys.
  - Change the storage scheme so these are **scoped keys** (example prefix: `aico:{deploymentId}:{tenantId}:...`):
    - access JWT
    - refresh token
    - stored user UUID + stored user profile
    - stored credentials (`src/utils/credentialStorage.ts`)
    - secure transport session material / client ID (anything `ensureSecureSession()` depends on)

- **Make the HTTP layer tenant-aware at a single choke point**
  - Centralize tenant scoping in `src/api/http.ts`:
    - Base URL from active deployment
    - Token from active tenant scope
    - Secure session from active deployment+tenant scope
  - Add a guard: when tenant isn’t selected, block all calls except login/tenant discovery.

- **Hard-reset behavior on tenant switch (data safety + UX)**
  - On `setActiveTenant()`:
    - invalidate/ignore in-flight requests (simple approach: bump a `requestEpoch` and drop late responses)
    - call `forceNewHandshake()` so encryption sessions cannot leak across tenants
    - clear in-memory caches/query results and route to a known-safe default screen

- **Token refresh must be tenant-scoped**
  - Update `src/utils/tokenManager.ts` to refresh the **active tenant’s** token using the **active tenant’s** refresh token.
  - Stop/restart refresh monitoring on tenant changes.

- **UX safety rails**
  - Always show `{deployment} / {tenant}` in the UI shell.
  - Use a deterministic tenant color badge (hash of `tenant_id`) to reduce operator mistakes.
  - For destructive mutations, include tenant name in confirmation text.

- **Roles and UI gating**
  - Split “admin” into at least two conceptual modes:
    - **platform_admin**: developer/cloud operator managing many enterprises
    - **tenant_admin**: enterprise admin managing their tenant(s)
  - Drive UI visibility from roles to reduce footguns (hide cross-tenant controls when not allowed).

## Required Backend/Gateway Support (AICO / `aico`)
Studio needs explicit endpoints to discover and switch tenants without relying on client-provided tenant headers.

- **Tenant discovery**
  - `GET /tenants` (or similar): list tenants the authenticated user can administer.

- **Tenant switch / session minting**
  - `POST /tenants/{tenant_id}/session` (or similar): returns a **tenant-scoped** `jwt_token` + `refresh_token`.
  - Rationale: tenant selection becomes an explicit, auditable action; all subsequent calls are scoped by JWT claims.

## Implementation Notes
- Keep tenant logic centralized to improve maintainability:
  - `TenantContext` for state
  - `src/api/config.ts` for scoped persistence
  - `src/api/http.ts` for request composition
- Avoid sprinkling tenant conditionals across feature components; they should just call APIs.

## Implementation Checklist (in order)
- [ ] Define the tenant/session API contracts (request/response shapes) for:
  - [ ] `GET /tenants`
  - [ ] `POST /tenants/{tenant_id}/session`
- [ ] Implement `GET /tenants` in the gateway (authz enforced; returns only tenants the user can administer).
- [ ] Implement `POST /tenants/{tenant_id}/session` in the gateway (mints tenant-scoped `jwt_token` + `refresh_token`).
- [ ] Add Studio API client functions for tenant discovery + tenant session minting (new `src/api/tenants.ts` or similar).
- [ ] Add `DeploymentContext` (or extend runtime config) to support multiple named deployments (each with `apiBaseUrl`).
- [ ] Add `TenantContext` with:
  - [ ] active `deploymentId/apiBaseUrl`
  - [ ] active `tenantId/tenantDisplayName`
  - [ ] `setActiveTenant()` that triggers a hard reset.
- [ ] Refactor `src/api/config.ts` to partition storage keys by `{deploymentId}:{tenantId}` for:
  - [ ] JWT + refresh token
  - [ ] stored user UUID + stored profile
- [ ] Refactor `src/utils/credentialStorage.ts` to partition stored credentials by `{deploymentId}:{tenantId}`.
- [ ] Refactor secure transport session persistence to be partitioned by `{deploymentId}:{tenantId}` (whatever `ensureSecureSession()` uses), and ensure tenant switch forces a new handshake.
- [ ] Update `src/api/http.ts` to be tenant-aware at the choke point:
  - [ ] resolve base URL from active deployment
  - [ ] resolve auth token from active tenant scope
  - [ ] add a guard: block calls when tenant is not selected (except login/tenant discovery)
  - [ ] implement a `requestEpoch` (or similar) so late responses from previous tenants are ignored.
- [ ] Update `src/utils/tokenManager.ts` so refresh is tenant-scoped and monitoring is restarted on tenant changes.
- [ ] Add tenant selection UX:
  - [ ] post-login tenant picker (only if multiple tenants)
  - [ ] persistent top-bar `{deployment}/{tenant}` switcher.
- [ ] Add UX safety rails:
  - [ ] tenant color badge
  - [ ] destructive action confirmations include tenant name
  - [ ] hide cross-tenant controls unless `platform_admin`.
- [ ] Add automated tests:
  - [ ] storage key partitioning tests (switch tenant ⇒ no shared token/profile)
  - [ ] tenant switch hard-reset tests (handshake reset + stale response drop)
  - [ ] API client tests for session minting + refresh per tenant.
