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

## Security Commands (`aico security`)

Manages master password setup and security operations for AICO's encrypted data layer.

### Available Commands

| Command | Description |
|---------|-------------|
| `setup` | First-time master password setup |
| `change-password` | Change master password (affects all databases) |
| `status` | Check security status and keyring information |
| `clear` | Clear stored master key (security incident recovery) |
| `test` | Test master password authentication |

### Examples

```bash
# First-time setup
aico security setup

# Check status
aico security status

# Change master password
aico security change-password

# Test authentication
aico security test
```

## Database Commands (`aico db`)

Manages encrypted database initialization and operations.

### Available Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize new encrypted database |
| `status` | Check database encryption status |
| `test` | Test database connection and operations |

### Examples

```bash
# Initialize LibSQL database (default)
aico db init --db-path ./my-app.db

# Initialize specific database type (future)
aico db init --db-path ./analytics.db --db-type duckdb

# Check database status
aico db status --db-path ./my-app.db

# Test database connection
aico db test --db-path ./my-app.db
```

### Workflow

1. **Setup master password**: `aico security setup`
2. **Initialize databases**: `aico db init`
3. **Verify setup**: `aico db status`

### Notes
- Uses `AICOKeyManager` for unified key management
- Supports multiple database types (currently LibSQL)
- PBKDF2 key derivation for LibSQL, Argon2id for others
- Stores passwords securely in system keyring
- Automatic salt management for database files

---
