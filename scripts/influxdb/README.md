# InfluxDB Optimization for AICO

This directory contains scripts to optimize InfluxDB performance for AICO Studio dashboards.

## Problem

InfluxDB performance degraded as data volume grew (~927,000 data points). Dashboard queries scanning hours/days of data caused 15-second load times.

## Solution

**Downsampling + Retention Policies**

1. **Pre-aggregate data** into 1-minute buckets automatically
2. **Keep raw data** for 7 days only
3. **Keep downsampled data** for 30 days
4. **Query downsampled data** for dashboards (60x less data)

## Setup Instructions

### 1. Run the setup script

```bash
cd /Users/mbo/Documents/dev/aico
uv run python scripts/influxdb/setup_influxdb.py
```

This will:
- Create `aico_telemetry_downsampled` bucket (30-day retention)
- Update `aico_telemetry` bucket to 7-day retention
- Create 6 downsampling tasks that run every minute

### 2. Wait for downsampled data

The tasks run every minute. Wait 1-2 minutes for initial data to populate.

### 3. Restart the backend

```bash
uv run aico start
```

The backend will now query the downsampled bucket for faster performance.

## Expected Performance Improvement

**Before:**
- `/system/metrics/all`: 15 seconds
- Scanning 100k-450k data points per query
- 15-20 complex Flux queries

**After:**
- `/system/metrics/all`: <2 seconds
- Scanning 1k-7k pre-aggregated points
- Same queries, but on downsampled data

## What Gets Downsampled

| Measurement | Downsampled To | Aggregation |
|-------------|----------------|-------------|
| `api_request` | `api_request_1m` | mean (duration), count (requests) |
| `messagebus_event` | `messagebus_event_1m` | sum (messages) |
| `scheduler_job` | `scheduler_job_1m` | mean (duration, success rate) |
| `memory_query` | `memory_query_1m` | mean (duration, result count) |
| `model_inference` | `model_inference_1m` | mean (duration, tokens) |

## Retention Policy

| Bucket | Retention | Purpose |
|--------|-----------|---------|
| `aico_telemetry` | 7 days | Raw high-resolution data |
| `aico_telemetry_downsampled` | 30 days | Pre-aggregated metrics |

## Monitoring

Check task status:
```bash
influx task list --org aico
```

View downsampled data:
```bash
influx query 'from(bucket: "aico_telemetry_downsampled") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "api_request_1m")' --org aico
```

## Troubleshooting

**Tasks not running?**
```bash
# Check task status
influx task list --org aico

# Enable a task
influx task update --id <task-id> --status active
```

**No downsampled data?**
- Wait 1-2 minutes after task creation
- Check InfluxDB logs: `docker logs influxdb`
- Verify raw data exists in `aico_telemetry` bucket

**Still slow?**
- Check if queries are using `aico_telemetry_downsampled` bucket
- Verify time windows are reduced (5m instead of 12m, 1h instead of 24h)
- Check InfluxDB CPU usage during queries

## Files

- `setup_influxdb.py` - Main setup script (run this)
- `setup_downsampling.flux` - Flux task definitions (reference)
- `setup_retention.flux` - Retention policy notes (reference)
- `README.md` - This file
