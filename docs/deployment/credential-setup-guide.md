# AICO Deployment Credential Setup Guide

## Quick Start: Deploy Everything with One Command

### Step 1: Set Required Environment Variables

```bash
# Generate secure credentials (run once)
export AICO_PG_PASSWORD=$(openssl rand -base64 32)
export AICO_INFLUX_ADMIN_PASSWORD=$(openssl rand -base64 32)
export AICO_INFLUX_ADMIN_TOKEN=$(openssl rand -base64 48)
export AICO_GRAFANA_PASSWORD=$(openssl rand -base64 32)

# Optional: Make non-interactive to prevent keyring prompts
export AICO_NONINTERACTIVE=true

# Save to .env file for persistence
cat > docker/.env << EOF
AICO_PG_PASSWORD=${AICO_PG_PASSWORD}
AICO_INFLUX_ADMIN_PASSWORD=${AICO_INFLUX_ADMIN_PASSWORD}
AICO_INFLUX_ADMIN_TOKEN=${AICO_INFLUX_ADMIN_TOKEN}
AICO_GRAFANA_PASSWORD=${AICO_GRAFANA_PASSWORD}
EOF

chmod 600 docker/.env
```

### Step 2: Deploy All Components

```bash
# Deploy infrastructure (databases, monitoring)
uv run aico deploy pg --nuke
uv run aico deploy influx --nuke
uv run aico deploy loki --nuke
uv run aico deploy grafana --nuke

# Deploy AICO services
uv run aico deploy gateway --nuke
uv run aico deploy core --nuke
uv run aico deploy modelservice --nuke

# Deploy Studio UI
uv run aico deploy studio --nuke --dev
```

### Step 3: Verify Deployment

```bash
# Check all containers are running
docker ps --filter "label=com.aico.project=aico"

# Check Studio is accessible
curl http://localhost:3002

# Check Gateway is accessible
curl http://localhost:8771/health
```

## Credential Management

### Environment Variables (Recommended for Containers)

All credentials can be provided via environment variables:

| Variable | Description | Required For |
|----------|-------------|--------------|
| `AICO_PG_PASSWORD` | PostgreSQL password | pg, gateway, core |
| `AICO_INFLUX_ADMIN_PASSWORD` | InfluxDB admin password | influx |
| `AICO_INFLUX_ADMIN_TOKEN` | InfluxDB API token | influx, telemetry |
| `AICO_GRAFANA_PASSWORD` | Grafana admin password | grafana |
| `AICO_NONINTERACTIVE` | Disable keyring prompts | all commands |

### Docker Secrets (Production)

For production deployments, use Docker secrets:

```yaml
# docker-compose.yml
services:
  gateway:
    secrets:
      - postgres_password
      - jwt_secret
    environment:
      AICO_PG_PASSWORD_FILE: /run/secrets/postgres_password

secrets:
  postgres_password:
    external: true
  jwt_secret:
    external: true
```

Create secrets:
```bash
echo "your-postgres-password" | docker secret create postgres_password -
echo "your-jwt-secret" | docker secret create jwt_secret -
```

### System Keyring (Local Development)

For local development, credentials are stored in macOS Keychain:

```bash
# Interactive mode will prompt for credentials and store in keyring
uv run aico security setup

# Credentials are automatically retrieved from keyring
uv run aico deploy pg
```

## Troubleshooting

### Command Hangs Waiting for Password

**Symptom**: Deploy command hangs with no output

**Cause**: Trying to access keyring in non-interactive mode

**Solution**:
```bash
export AICO_NONINTERACTIVE=true
# Provide credentials via environment variables
export AICO_PG_PASSWORD="your-password"
uv run aico deploy pg
```

### Credentials Not Found

**Symptom**: "Generating ephemeral credentials" warning

**Cause**: No credentials found in any source

**Solution**: Set environment variables or run in interactive mode to store in keyring

### Docker Container Can't Access Keyring

**Symptom**: Container fails to start or hangs

**Cause**: Containers can't access host keyring

**Solution**: Always use environment variables or Docker secrets for containers

## Complete Deployment Script

```bash
#!/bin/bash
set -e

# Generate and export credentials
export AICO_PG_PASSWORD=$(openssl rand -base64 32)
export AICO_INFLUX_ADMIN_PASSWORD=$(openssl rand -base64 32)
export AICO_INFLUX_ADMIN_TOKEN=$(openssl rand -base64 48)
export AICO_GRAFANA_PASSWORD=$(openssl rand -base64 32)
export AICO_NONINTERACTIVE=true

# Save to .env
mkdir -p docker
cat > docker/.env << EOF
AICO_PG_PASSWORD=${AICO_PG_PASSWORD}
AICO_INFLUX_ADMIN_PASSWORD=${AICO_INFLUX_ADMIN_PASSWORD}
AICO_INFLUX_ADMIN_TOKEN=${AICO_INFLUX_ADMIN_TOKEN}
AICO_GRAFANA_PASSWORD=${AICO_GRAFANA_PASSWORD}
EOF

# Deploy everything
echo "Deploying infrastructure..."
uv run aico deploy pg --nuke
uv run aico deploy influx --nuke
uv run aico deploy loki --nuke
uv run aico deploy grafana --nuke

echo "Deploying AICO services..."
uv run aico deploy gateway --nuke
uv run aico deploy core --nuke
uv run aico deploy modelservice --nuke

echo "Deploying Studio..."
uv run aico deploy studio --nuke --dev

echo "Deployment complete!"
echo "Studio: http://localhost:3002"
echo "Gateway: http://localhost:8771"
echo "Grafana: http://localhost:3001"
```

Save as `deploy-all.sh` and run:
```bash
chmod +x deploy-all.sh
./deploy-all.sh
```
