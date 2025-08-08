# Versioning Approach

AICO uses modern, best-practice versioning to ensure stability and clarity across all main components. Update the VERSIONS file and run the version propagation script to sync all components. This document summarizes our approach.

## Component Versioning

- **Backend:** Uses [Semantic Versioning (SemVer)](https://semver.org/) (MAJOR.MINOR.PATCH). All API and contract changes follow SemVer rules. Backend version is exposed via `/api/version`.
- **Frontend, CLI, Studio:** Each has its own SemVer version. Releases are independent but must declare compatible backend/API versions.

## API Versioning

- All APIs are explicitly versioned using a version prefix (e.g., `/api/v1/`).
- Breaking changes require bumping the API version. Old versions are supported for a deprecation window.

## Compatibility Management

- Each client (Frontend, CLI, Studio) declares the minimum and maximum supported backend/API version in its metadata/config.
- On startup, clients check backend version and warn or block if incompatible.

## Release Coordination

- Backend is the single source of truth for all major component versions (see the root VERSIONS file). Clients track backend releases and update as needed.
- All releases and changelogs must state compatibility and breaking changes.

## Examples from Similar Projects

- **VS Code + Language Servers:** Protocol version checks on connect.
- **JupyterLab + Jupyter Server:** Client checks API version and warns if mismatched.
- **Matrix (Element + Synapse):** API versioning and compatibility checks.

## Summary Table

| Component | Versioning Scheme | Compatibility Management           |
|-----------|-------------------|------------------------------------|
| Shared    | SemVer            | Foundation library for CLI/Backend |
| Backend   | SemVer            | API versioning, `/api/vX/` path    |
| Frontend  | SemVer            | Declares required backend version  |
| CLI       | SemVer            | Declares required backend version  |
| Studio    | SemVer            | Declares required backend version  |


