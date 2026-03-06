#!/bin/bash
set -e

# AICO Backend Entrypoint - Load credentials from secrets

echo "🔐 AICO Backend Entrypoint: Checking credentials..."

# Check if AICO_PG_PASSWORD is set; if not, load from Compose secret
if [ -z "$AICO_PG_PASSWORD" ]; then
    if [ -f "/run/secrets/pg_password" ]; then
        export AICO_PG_PASSWORD=$(cat /run/secrets/pg_password)
        echo "✅ Loaded PostgreSQL password from /run/secrets/pg_password"
    else
        echo "❌ AICO_PG_PASSWORD not set and /run/secrets/pg_password not found"
        exit 1
    fi
else
    echo "✅ Using PostgreSQL password from environment"
fi

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if PGPASSWORD="$AICO_PG_PASSWORD" psql -h "$AICO_PG_HOST" -U postgres -d postgres -c '\q' 2>/dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ PostgreSQL failed to become ready after $max_attempts attempts"
        exit 1
    fi
    
    echo "   Attempt $attempt/$max_attempts - PostgreSQL not ready yet, waiting..."
    sleep 2
done

# Execute the command passed to the entrypoint
echo "🚀 Starting AICO backend service..."
exec "$@"
