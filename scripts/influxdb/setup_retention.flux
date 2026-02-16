// InfluxDB Retention Policies for AICO
// This script sets up retention policies to automatically delete old data
// Run this script once to configure retention

// ============================================================================
// Retention Policy 1: Raw telemetry data (7 days)
// ============================================================================
// Keep raw high-resolution data for 7 days only
// This applies to the main aico_telemetry bucket

// Note: Retention is set at bucket creation time or via CLI:
// influx bucket update --id <bucket-id> --retention 168h

// ============================================================================
// Retention Policy 2: Downsampled data (30 days)
// ============================================================================
// Keep 1-minute aggregates for 30 days
// This applies to the aico_telemetry_downsampled bucket

// Note: Create the downsampled bucket with:
// influx bucket create --name aico_telemetry_downsampled --org aico --retention 720h

// ============================================================================
// CLI Commands to Set Up Retention
// ============================================================================

// 1. Update main bucket to 7-day retention:
//    influx bucket update --name aico_telemetry --org aico --retention 168h

// 2. Create downsampled bucket with 30-day retention:
//    influx bucket create --name aico_telemetry_downsampled --org aico --retention 720h

// 3. Verify retention settings:
//    influx bucket list --org aico
