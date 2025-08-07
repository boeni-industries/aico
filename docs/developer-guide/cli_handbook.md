# AICO CLI Handbook

## Overview
The `aico` command-line interface (CLI) is your central tool for automating, administering, and interacting with the AICO system. This handbook covers practical usage, command syntax, and real-world examples for developers and power users.

---

## Version Command Group

### Purpose
Manage and synchronize the versioning of all major AICO system parts (CLI, backend, frontend, studio) from a single source of truth.

### Usage Summary

```sh
aico version [COMMAND] [OPTIONS]
```

### Available Commands

| Command                                | Description                                             |
|----------------------------------------|---------------------------------------------------------|
| `aico version [part]`                  | Print the current version of a part or all parts        |
| `aico version sync`                    | Sync all canonical project versions from VERSIONS file  |
| `aico version bump [part] [level]`     | Bump version (major, minor, patch) and propagate/tag    |
| `aico version check`                   | Validate all canonical versions vs. VERSIONS            |
| `aico version history [part]`          | Show git tag history for a part                         |
| `aico version next [part] [level]`     | Preview next version number without changing anything   |

- `[part]` can be: `cli`, `backend`, `frontend`, `studio`, or `all` (default: all)
- `[level]` can be: `major`, `minor`, or `patch`

### Examples

- Print all versions:
  ```sh
  aico version
  ```
- Print backend version:
  ```sh
  aico version backend
  ```
- Sync all canonical versions from VERSIONS:
  ```sh
  aico version sync
  ```
- Bump CLI version (patch):
  ```sh
  aico version bump cli patch
  ```
- Preview next frontend minor version:
  ```sh
  aico version next frontend minor
  ```
- Check for version drift:
  ```sh
  aico version check
  ```
- Show studio version history:
  ```sh
  aico version history studio
  ```

### UX Principles
- All commands provide clear, colorized, and actionable output.
- Incomplete or ambiguous commands trigger a helpful, predictive help text.
- Destructive actions (bump, sync) require confirmation or a `--yes` flag.
- Tabular and markdown output is used where appropriate.
- Errors and warnings are highlighted for quick identification.

### Advanced Options
- `--dry-run` (where supported): Preview changes without applying them.
- `--no-tag` (for bump): Skip git tagging when bumping version.

### Notes
- The source of truth for all versions is the `VERSIONS` file at the project root.
- Canonical versions are propagated to: `/cli`, `/backend`, `/frontend`, `/studio`.
- Versioning follows [Semantic Versioning](https://semver.org/).

---

For more details on versioning policy, see the [developer guide](./versioning.md).

---

## Security Command Group

The `security` command group enables secure management of cryptographic keys, master passwords, and encrypted filesystem operations. It is designed for both administrators and developers to manage foundational security features from the CLI.

### Usage Summary

```sh
aico security [COMMAND] [OPTIONS]
```

### Available Commands

| Command                                 | Description                                             |
|------------------------------------------|---------------------------------------------------------|
| `aico security key init`                 | Set up master password and initialize key storage        |
| `aico security key status`               | Show key status and authentication method               |
| `aico security key change-password`      | Change the master password                              |
| `aico security key clear`                | Remove all stored keys and authentication state         |
| `aico security fs init`                  | Initialize encrypted data directory (securefs)         |
| `aico security fs mount`                 | Mount encrypted directory                               |
| `aico security fs unmount`               | Unmount encrypted directory                             |
| `aico security fs status`                | Show status of encrypted mounts                         |
| `aico security audit log`                | Show recent security events and audit log               |
| `aico security audit check`              | Run security health checks and report findings          |

### Examples

- Initialize master password and keys:
  ```sh
  aico security key init
  ```
- Mount encrypted data directory:
  ```sh
  aico security fs mount --dir ~/.aico/data.enc
  ```
- Check key status:
  ```sh
  aico security key status
  ```
- Run security audit check:
  ```sh
  aico security audit check
  ```

### Notes
- `securefs` must be installed (see [installation guide](https://github.com/netheril96/securefs)).
- `python-securefs` Python bindings may be used if available, otherwise subprocess calls are used.
- Key management is handled by the shared library (`AICOKeyManager`).
- Audit logs and health checks are extensible for future compliance needs.

---
