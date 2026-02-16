# PostgreSQL Configuration for AICO

## Overview

This directory contains production-grade PostgreSQL configuration for self-hosted AICO deployments.

## Files

- **postgresql.conf** - Main Postgres configuration file with optimized settings for:
  - SSD storage
  - 4GB RAM baseline (scalable)
  - Connection pooling
  - Query performance (JIT, parallel workers)
  - Autovacuum tuning
  - Logging and monitoring

## Configuration Approach

**Best Practice for Self-Hosting:**
- ✅ Server-level settings → `postgresql.conf` (version-controlled, portable)
- ✅ Connection-level settings → Application code (`connection.py`)
- ✅ Secrets → Environment variables (never in config files)

## Memory Sizing

The default configuration assumes **4GB RAM**. Adjust for your hardware:

### 4GB RAM (Default)
```conf
shared_buffers = 1GB
effective_cache_size = 3GB
work_mem = 16MB
```

### 8GB RAM
```conf
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 32MB
```

### 16GB RAM
```conf
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB
```

## Usage

### Local Development (Docker Compose)
```bash
# Configuration is automatically mounted and used
docker compose -f docker/docker-compose.local.yml up -d postgres
```

### Production Deployment

**Option 1: Docker/Podman**
```bash
docker run -d \
  -v ./postgresql.conf:/etc/postgresql/postgresql.conf:ro \
  -e POSTGRES_PASSWORD=... \
  postgres:18.1 \
  -c config_file=/etc/postgresql/postgresql.conf
```

**Option 2: Kubernetes**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-config
data:
  postgresql.conf: |
    # Copy contents of postgresql.conf here
---
apiVersion: apps/v1
kind: StatefulSet
spec:
  template:
    spec:
      containers:
      - name: postgres
        volumeMounts:
        - name: config
          mountPath: /etc/postgresql
      volumes:
      - name: config
        configMap:
          name: postgres-config
```

**Option 3: Bare Metal/VM**
```bash
# Copy to Postgres data directory
cp postgresql.conf /var/lib/postgresql/data/
systemctl restart postgresql
```

## Monitoring

### Check Active Configuration
```sql
-- Show all non-default settings
SELECT name, setting, source 
FROM pg_settings 
WHERE source != 'default';

-- Check specific setting
SHOW shared_buffers;
SHOW work_mem;
```

### Performance Monitoring
```sql
-- Database statistics
SELECT * FROM pg_stat_database WHERE datname = 'aico';

-- Slow queries (requires pg_stat_statements extension)
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Active connections
SELECT * FROM pg_stat_activity;
```

## Tuning Guidelines

### When to Adjust

**Increase `shared_buffers` if:**
- You have more RAM available
- Cache hit ratio is low (<90%)
- Query: `SELECT sum(blks_hit)*100/sum(blks_hit+blks_read) FROM pg_stat_database;`

**Increase `work_mem` if:**
- Queries are doing disk sorts (check `EXPLAIN ANALYZE`)
- You have RAM available
- Few concurrent connections

**Increase `max_parallel_workers` if:**
- You have more CPU cores
- Queries are CPU-bound
- Large table scans are common

### Performance Checklist

- [ ] Verify JIT is enabled: `SHOW jit;`
- [ ] Check cache hit ratio: Should be >90%
- [ ] Monitor connection count: Should be <max_connections
- [ ] Review slow query log: Queries >1s are logged
- [ ] Check autovacuum is running: `SELECT * FROM pg_stat_progress_vacuum;`

## Troubleshooting

### Configuration Not Applied
```bash
# Verify config file is mounted
docker exec aico-postgres cat /etc/postgresql/postgresql.conf

# Check Postgres is using it
docker exec aico-postgres psql -U postgres -c "SHOW config_file;"
```

### Out of Memory
```bash
# Reduce shared_buffers or work_mem
# Rule: shared_buffers + (work_mem * max_connections) < Total RAM
```

### Slow Queries
```sql
-- Enable query logging temporarily
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log queries >100ms
SELECT pg_reload_conf();
```

## References

- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [PGTune](https://pgtune.leopard.in.ua/) - Configuration generator
- [PostgreSQL 18 Documentation](https://www.postgresql.org/docs/18/)
