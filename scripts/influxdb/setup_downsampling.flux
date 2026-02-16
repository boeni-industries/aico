// InfluxDB Downsampling Tasks for AICO Metrics
// This script creates continuous aggregation tasks to improve dashboard performance
// Run this script once to set up all downsampling tasks

// ============================================================================
// Task 1: Downsample API Request Metrics (1-minute aggregates)
// ============================================================================
option task = {
    name: "downsample_api_requests",
    every: 1m,
    offset: 10s
}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "api_request")
    |> filter(fn: (r) => r._field == "duration_ms_i" or r._field == "status_code_i")
    |> aggregateWindow(
        every: 1m,
        fn: mean,
        createEmpty: false
    )
    |> set(key: "_measurement", value: "api_request_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")

// ============================================================================
// Task 2: Downsample Message Bus Events (1-minute aggregates)
// ============================================================================
option task = {
    name: "downsample_messagebus",
    every: 1m,
    offset: 15s
}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "messagebus_event")
    |> filter(fn: (r) => r._field == "message_count_i" or r._field == "latency_ms_i")
    |> aggregateWindow(
        every: 1m,
        fn: sum,  // Sum message counts, mean for latency
        createEmpty: false
    )
    |> set(key: "_measurement", value: "messagebus_event_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")

// ============================================================================
// Task 3: Downsample Scheduler Jobs (1-minute aggregates)
// ============================================================================
option task = {
    name: "downsample_scheduler",
    every: 1m,
    offset: 20s
}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "scheduler_job")
    |> filter(fn: (r) => r._field == "duration_ms_i" or r._field == "success_b")
    |> aggregateWindow(
        every: 1m,
        fn: mean,
        createEmpty: false
    )
    |> set(key: "_measurement", value: "scheduler_job_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")

// ============================================================================
// Task 4: Downsample Memory Queries (1-minute aggregates)
// ============================================================================
option task = {
    name: "downsample_memory_queries",
    every: 1m,
    offset: 25s
}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "memory_query")
    |> filter(fn: (r) => r._field == "duration_ms_i" or r._field == "result_count_i")
    |> aggregateWindow(
        every: 1m,
        fn: mean,
        createEmpty: false
    )
    |> set(key: "_measurement", value: "memory_query_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")

// ============================================================================
// Task 5: Downsample Model Inference (1-minute aggregates)
// ============================================================================
option task = {
    name: "downsample_model_inference",
    every: 1m,
    offset: 30s
}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "model_inference")
    |> filter(fn: (r) => r._field == "duration_ms_i" or r._field == "token_count_i")
    |> aggregateWindow(
        every: 1m,
        fn: mean,
        createEmpty: false
    )
    |> set(key: "_measurement", value: "model_inference_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")

// ============================================================================
// Task 6: Count-based aggregates for API requests (for RPS calculations)
// ============================================================================
option task = {
    name: "downsample_api_counts",
    every: 1m,
    offset: 35s
}

from(bucket: "aico_telemetry")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "api_request")
    |> filter(fn: (r) => r._field == "status_code_i")
    |> aggregateWindow(
        every: 1m,
        fn: count,
        createEmpty: false
    )
    |> set(key: "_measurement", value: "api_request_counts_1m")
    |> to(bucket: "aico_telemetry_downsampled", org: "aico")
