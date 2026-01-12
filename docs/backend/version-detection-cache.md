# Database Version Detection & Caching System

## Overview

The version detection system automatically queries database systems to retrieve their exact versions, with intelligent caching to minimize overhead while keeping information accurate.

## Architecture

### Components

1. **`DatabaseVersionDetector`** - Main detection engine
2. **`VersionCache`** - JSON-based disk cache with TTL
3. **CLI Commands** - Management interface via `aico versions`
4. **Integration** - Used by topology endpoint in `router.py`

## How the JSON/Disk-Based Cache Works

### Cache Location

```
~/Library/Application Support/aico/cache/database_versions.json
```

On Linux: `~/.local/share/aico/cache/database_versions.json`

### Cache Structure

```json
{
  "PostgreSQL": {
    "name": "PostgreSQL",
    "version": "18.1",
    "detected_at": "2026-01-12T14:30:00.000000",
    "detection_method": "docker exec + SELECT version()"
  },
  "InfluxDB": {
    "name": "InfluxDB",
    "version": "2.8.0",
    "detected_at": "2026-01-12T14:30:00.000000",
    "detection_method": "docker exec + influxd version"
  },
  "ChromaDB": {
    "name": "ChromaDB",
    "version": "0.5.6",
    "detected_at": "2026-01-12T14:30:00.000000",
    "detection_method": "python package version"
  }
}
```

### Cache Behavior

#### 1. **First Request (Cache Miss)**

```python
# User requests topology data
GET /api/v1/operations/topology

# Version detector checks cache
cached = cache.get("PostgreSQL")  # Returns None (no cache)

# Detector runs actual detection
version = await _detect_postgresql_version()  # Queries docker container

# Result is cached with timestamp
cache.set(DatabaseVersion(
    name="PostgreSQL",
    version="18.1",
    detected_at="2026-01-12T14:30:00",
    detection_method="docker exec + SELECT version()"
))

# Returns: "18.1"
```

**Performance**: ~200-500ms (actual database query)

#### 2. **Subsequent Requests (Cache Hit)**

```python
# User requests topology data again
GET /api/v1/operations/topology

# Version detector checks cache
cached = cache.get("PostgreSQL")  # Returns cached entry

# Check if cache is still valid (< 24 hours old)
age = datetime.utcnow() - cached.detected_at  # 2 hours
if age < timedelta(hours=24):
    return cached.version  # "18.1" - NO database query!

# Returns: "18.1"
```

**Performance**: ~1-2ms (disk read only)

#### 3. **Expired Cache (After 24 Hours)**

```python
# User requests topology data 25 hours later
GET /api/v1/operations/topology

# Version detector checks cache
cached = cache.get("PostgreSQL")  # Returns cached entry

# Check if cache is still valid
age = datetime.utcnow() - cached.detected_at  # 25 hours
if age > timedelta(hours=24):
    # Cache expired - re-detect
    version = await _detect_postgresql_version()
    cache.set(new_version)  # Update cache with new timestamp
    return version

# Returns: "18.1" (or new version if upgraded)
```

**Performance**: ~200-500ms (re-detection triggered)

### Cache TTL (Time-To-Live)

- **Default**: 24 hours
- **Configurable**: Pass `cache_ttl_hours` to `DatabaseVersionDetector()`
- **Rationale**: Database versions rarely change, but we want to detect upgrades within a day

### Cache Invalidation

#### Manual Invalidation (CLI)

```bash
# Invalidate all cached versions
aico versions refresh

# Invalidate specific database
aico versions refresh PostgreSQL
```

#### Programmatic Invalidation

```python
from backend.services.version_detector import get_version_detector

detector = get_version_detector()

# Invalidate all
detector.invalidate_cache()

# Invalidate specific
detector.invalidate_cache("PostgreSQL")
```

## Detection Methods

### PostgreSQL
```bash
docker exec aico-postgres psql -U postgres -t -c "SELECT version()"
```
Parses output: `PostgreSQL 18.1 on x86_64-pc-linux-gnu...`

### InfluxDB
```bash
docker exec aico-influxdb influxd version
```
Parses output: `InfluxDB v2.8.0 (git: ...) build_date: ...`

### ChromaDB
```python
import chromadb
version = chromadb.__version__  # "0.5.6"
```

### LMDB
```python
import lmdb
version = lmdb.version()  # (0, 9, 31)
version_str = "0.9.31"
```

### Ollama
```bash
curl http://localhost:11434/api/version
```
Parses JSON: `{"version": "0.5.1"}`

## Error Handling & Logging

### Detection Failures

All detection failures are logged as **ERROR** level (not debug/warning):

```python
logger.error(f"PostgreSQL version detection FAILED - using fallback: 18.1")
logger.error(f"InfluxDB version query failed with exit code 1: stderr output")
logger.error(f"ChromaDB package not installed - cannot detect version")
```

### Fallback Behavior

When detection fails, the system falls back to hardcoded defaults:

```python
DEFAULT_VERSIONS = {
    "PostgreSQL": "18.1",
    "InfluxDB": "2.8.0",
    "ChromaDB": "0.5.x",
    "LMDB": "0.9.x",
    "Ollama": "0.5.x",
}
```

**Important**: Fallbacks are **NOT** a replacement for working detection. They exist only for:
1. Initial startup before containers are ready
2. Development environments without all services
3. Graceful degradation during outages

**Production expectation**: Detection should always succeed. Fallback usage indicates a problem that needs investigation.

## Performance Characteristics

### Cache Hit (Normal Operation)
- **Latency**: 1-2ms
- **I/O**: Single JSON file read (~1KB)
- **Network**: None
- **CPU**: Minimal (JSON parsing)

### Cache Miss (First Request or Expired)
- **Latency**: 200-500ms
- **I/O**: Docker exec + JSON write
- **Network**: Docker socket communication
- **CPU**: Process spawning + parsing

### Cache Write
- **Latency**: 5-10ms
- **I/O**: JSON file write (~1KB)
- **Atomic**: Uses write-to-temp + rename pattern

## Monitoring & Debugging

### Check Cache Status

```bash
# View all cached versions with age
aico versions cache-info

# Output:
# ┌──────────────┬─────────┬──────────────────┬──────┐
# │ Database     │ Version │ Detected At      │ Age  │
# ├──────────────┼─────────┼──────────────────┼──────┤
# │ PostgreSQL   │ 18.1    │ 2026-01-12 14:30 │ 2.3h │
# │ InfluxDB     │ 2.8.0   │ 2026-01-12 14:30 │ 2.3h │
# └──────────────┴─────────┴──────────────────┴──────┘
```

### View Logs

```bash
# Check for detection failures
aico logs --level ERROR --filter "version detection"

# Expected on success:
# [INFO] PostgreSQL version detected successfully: 18.1
# [INFO] InfluxDB version detected successfully: 2.8.0

# Errors indicate problems:
# [ERROR] PostgreSQL version detection FAILED - using fallback: 18.1
# [ERROR] InfluxDB version query failed with exit code 1
```

### Force Re-Detection

```bash
# Force fresh detection (bypasses cache)
aico versions refresh

# Verify detection works
aico versions show PostgreSQL
```

## Integration Example

### In Topology Endpoint

```python
from backend.services.version_detector import get_version_detector

@router.get("/topology")
async def get_system_topology():
    # Get detector singleton
    detector = get_version_detector()
    
    # Get all versions (uses cache if valid)
    db_versions = await detector.get_all_versions()
    
    # Use in service nodes
    services = [
        ServiceNode(
            id="postgresql",
            name="PostgreSQL",
            version=db_versions.get("PostgreSQL", "18.1"),  # Fallback if detection fails
            ...
        ),
        ...
    ]
```

## Best Practices

### ✅ DO

- Monitor logs for detection failures
- Use CLI to verify detection works after upgrades
- Rely on cache for normal operations
- Investigate any fallback usage in production

### ❌ DON'T

- Don't hardcode versions in application code
- Don't ignore detection failure logs
- Don't treat fallbacks as acceptable long-term
- Don't manually edit the cache JSON file

## Troubleshooting

### Problem: Detection Always Fails

**Symptoms**: Logs show `version detection FAILED` on every request

**Causes**:
1. Docker containers not running
2. Container names don't match (`aico-postgres`, `aico-influxdb`)
3. Docker socket permissions
4. Network connectivity issues

**Solution**:
```bash
# Check containers are running
docker ps | grep aico

# Test manual detection
docker exec aico-postgres psql -U postgres -t -c "SELECT version()"

# Force re-detection
aico versions refresh
```

### Problem: Stale Versions After Upgrade

**Symptoms**: Topology shows old version after database upgrade

**Cause**: Cache hasn't expired yet (< 24 hours)

**Solution**:
```bash
# Invalidate cache to force re-detection
aico versions refresh PostgreSQL
```

### Problem: Cache File Corruption

**Symptoms**: JSON parse errors in logs

**Solution**:
```bash
# Delete cache file (will be recreated)
rm ~/Library/Application\ Support/aico/cache/database_versions.json

# Verify recreation
aico versions list
```

## Future Enhancements

Potential improvements for consideration:

1. **Configurable TTL per database** - Some may change more frequently
2. **Version change notifications** - Alert when upgrades detected
3. **Health check integration** - Detect version mismatches
4. **Metrics export** - Track detection success rates
5. **Distributed cache** - Share cache across multiple backend instances
