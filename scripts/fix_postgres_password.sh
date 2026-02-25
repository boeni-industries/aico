#!/bin/bash
# Fix PostgreSQL password to match docker/.env

set -e

# Get the password from .env
PG_PASSWORD=$(grep AICO_PG_PASSWORD docker/.env | cut -d= -f2)

if [ -z "$PG_PASSWORD" ]; then
    echo "Error: AICO_PG_PASSWORD not found in docker/.env"
    exit 1
fi

echo "Updating PostgreSQL password to match docker/.env..."

# Update the password using docker exec with PGPASSWORD
docker exec -e PGPASSWORD="$PG_PASSWORD" aico-postgres psql -U postgres -c "ALTER USER postgres WITH PASSWORD '$PG_PASSWORD';" 2>/dev/null || \
docker exec aico-postgres psql -U postgres -c "ALTER USER postgres WITH PASSWORD '$PG_PASSWORD';" || \
{
    echo "Failed to update password. PostgreSQL may need to be recreated."
    echo "Run: docker-compose -f docker/docker-compose.local.yml up -d --force-recreate postgres"
    exit 1
}

echo "✓ PostgreSQL password updated successfully"
echo "✓ Restarting gateway to reconnect..."
docker restart aico-gateway

echo "✓ Done! Try logging in to Studio now."
