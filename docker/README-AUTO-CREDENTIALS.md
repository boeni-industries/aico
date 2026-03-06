# Zero-Effort Credential Management for Docker

## Overview

The AICO Docker setup now includes **automatic credential generation** with zero manual configuration required.

## How It Works

1. **Entrypoint Script** (`entrypoint-backend.sh`):
   - Runs before backend services start
   - Checks if `AICO_PG_PASSWORD` exists
   - Auto-generates secure 32-character password if missing
   - Saves to `docker/.env` for persistence across restarts
   - Waits for PostgreSQL to be ready before starting services

2. **Docker Compose Integration**:
   - Backend containers mount `docker/.env` file
   - Credentials persist across container rebuilds
   - First container to start generates the password
   - Subsequent containers read from the same file

3. **PostgreSQL Container**:
   - Reads password from environment variable
   - Uses the auto-generated password automatically

## Usage

Just start Docker Compose - credentials are handled automatically:

```bash
cd docker
docker-compose -f docker-compose.local.yml up -d
```

**That's it!** No manual password setup required.

## What Happens on First Run

1. Gateway/Core container starts
2. Entrypoint detects missing `AICO_PG_PASSWORD`
3. Generates secure password: `openssl rand -base64 32`
4. Saves to `docker/.env`
5. Waits for PostgreSQL to accept connections
6. Starts backend service

## Credential Persistence

The `docker/.env` file is created in the `docker/` directory and contains:

```bash
# Auto-generated AICO credentials
AICO_PG_PASSWORD=<secure-32-char-password>
```

This file:
- ✅ Persists across container restarts
- ✅ Shared between all backend containers
- ✅ Automatically created on first run
- ✅ Reused on subsequent runs

## Manual Override (Optional)

If you want to use a specific password:

```bash
# Create docker/.env before starting containers
echo "AICO_PG_PASSWORD=your_custom_password" > docker/.env
docker-compose -f docker-compose.local.yml up -d
```

## Troubleshooting

If you see "no password supplied" errors:

1. Check if `docker/.env` exists and contains `AICO_PG_PASSWORD`
2. Rebuild containers to ensure entrypoint script is included:
   ```bash
   docker-compose -f docker-compose.local.yml build
   docker-compose -f docker-compose.local.yml up -d
   ```

## Security Notes

- Passwords are 32 characters, base64-encoded random data
- The `docker/.env` file has 600 permissions (owner read/write only)
- Passwords are never logged or displayed in plain text
- Each deployment gets a unique password unless manually overridden
