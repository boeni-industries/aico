#!/bin/bash
set -e

# AICO Backend Entrypoint - Auto-generates credentials if missing
# This ensures PostgreSQL password exists before backend services start

echo "🔐 AICO Backend Entrypoint: Checking credentials..."

# Ensure docker directory exists
mkdir -p /app/docker

# Check if AICO_PG_PASSWORD is set
if [ -z "$AICO_PG_PASSWORD" ]; then
    echo "⚠️  AICO_PG_PASSWORD not set - attempting auto-generation..."
    
    # Try to load from docker/.env if it exists
    if [ -f "/app/docker/.env" ]; then
        echo "📄 Loading credentials from docker/.env..."
        set -a
        source /app/docker/.env
        set +a
    fi
    
    # If still not set, generate it
    if [ -z "$AICO_PG_PASSWORD" ]; then
        echo "🔧 Auto-generating PostgreSQL password..."
        # Generate a secure 32-character password
        export AICO_PG_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
        
        # Save to docker/.env for persistence
        if [ ! -f "/app/docker/.env" ]; then
            echo "# Auto-generated AICO credentials" > /app/docker/.env
            echo "AICO_PG_PASSWORD=$AICO_PG_PASSWORD" >> /app/docker/.env
            chmod 600 /app/docker/.env
            echo "✅ Generated and saved PostgreSQL password to docker/.env"
        else
            # Append if file exists but password wasn't there
            if ! grep -q "AICO_PG_PASSWORD" /app/docker/.env; then
                echo "AICO_PG_PASSWORD=$AICO_PG_PASSWORD" >> /app/docker/.env
                echo "✅ Generated and saved PostgreSQL password to docker/.env"
            fi
        fi
    else
        echo "✅ Using PostgreSQL password from docker/.env"
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
