#!/bin/bash
set -e

# AICO Gateway Entrypoint - Minimal dependencies (no PostgreSQL wait)

echo "🔐 AICO Gateway Entrypoint: Starting..."

# Gateway doesn't need PostgreSQL - it's stateless and routes to Core via NATS
# Wait for NATS to be ready instead
echo "⏳ Waiting for NATS to be ready..."
max_attempts=15
attempt=0
nats_host="${AICO_NATS_HOST:-nats}"
nats_port="${AICO_NATS_PORT:-4222}"

while [ $attempt -lt $max_attempts ]; do
    # Use Python to check NATS connectivity (more reliable than nc)
    if python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('$nats_host', $nats_port)); s.close()" 2>/dev/null; then
        echo "✅ NATS is ready at $nats_host:$nats_port!"
        break
    fi
    
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "⚠️  NATS not ready after $max_attempts attempts - starting anyway (will retry on connect)"
        break
    fi
    
    echo "   Attempt $attempt/$max_attempts - NATS not ready yet, waiting..."
    sleep 2
done

# Execute the command passed to the entrypoint
echo "🚀 Starting AICO Gateway service..."
exec "$@"
