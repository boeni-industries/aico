"""
AICO InfluxDB Telemetry Schema

Org:    aico
Bucket: aico_telemetry

This file documents the *logical* telemetry schema for InfluxDB using
annotated line protocol examples. It replaces the OTEL_* tables that were
previously stored in LibSQL / Postgres and is the canonical source of truth
for time-series telemetry.

This schema is designed to be:
- Backed by OpenTelemetry metrics and attributes
- Aligned with the Telemetry Architecture docs
- Extensible for future categories (AI behavior, research metrics, etc.)

The measurements below are the initial, concrete mapping of the former
`otel_api_requests`, `otel_model_inferences`, `otel_memory_queries`,
`otel_scheduler_jobs`, and `otel_message_bus_events` tables into InfluxDB.

NOTE: This file is *documentation + examples*. `aico influx init` should use
it to configure buckets, retention policies, and validation, but it does not
execute line protocol directly.
"""

###############################################################################
# Global conventions
###############################################################################

# - All measurements share a core set of tags where applicable:
#   - service      : logical service name (api-gateway, modelservice, backend, etc.)
#   - deployment   : environment/mode (dev, pro, production, casual)
#   - host         : hostname or node identifier
#   - instance     : instance ID if running multiple replicas (optional)
#   - version      : semantic version of the component (e.g. 0.5.2) (optional)
#
# - Timestamps are written in RFC3339 by clients; Influx stores as ns internally.
# - Fields use the following broad types:
#   - _f   (float)   : latency, rates, scores
#   - _i   (integer) : counts, cardinalities
#   - _s   (string)  : labels, discrete enums
#   - _b   (boolean) : success flags
#
# - Retention policy (configured via `aico influx init`):
#   - Default: 30 days (720h) for all measurements
#   - Future: Separate retention tiers or downsampling for long-term analytics
#
# - Cardinality best practices:
#   - Keep tag cardinality low (< 10k unique values per tag)
#   - Avoid high-cardinality tags: user IDs, session IDs, request IDs, UUIDs
#   - Use fields (not tags) for high-cardinality data
#   - Normalize paths to route templates (e.g., /v1/messages/{id}, not /v1/messages/12345)
#
# - Aggregation strategy:
#   - OTel exporters write pre-aggregated points (e.g., avg latency over export interval)
#   - Export interval: 60s (default) or configurable
#   - Each point represents a summary of metrics collected during that interval


###############################################################################
# Measurement: api_request
#
# Replaces: otel_api_requests
# Source:   OTel metric "aico.api.request.duration" (histogram)
###############################################################################

# Tags:
# - service       : e.g. "api-gateway"
# - deployment    : e.g. "dev", "production"
# - host          : hostname
# - method        : HTTP method (GET, POST, ...)
# - path          : normalized route template (e.g. /v1/messages/{id})
# - protocol      : "HTTP", "REST", "GRPC" (uppercased)
# - category      : high-level API category (auth, chat, admin, etc.)
# - status_class  : derived from status_code (2xx, 4xx, 5xx)

# Fields:
# - status_code_i    : exact HTTP status code
# - latency_ms_f     : latency per request (ms; pre-aggregated average from OTel)
# - request_body_b   : whether a request body was present (optional)
# - response_size_i  : response size in bytes (optional)
# - error_message_s  : redacted/short error label if present (optional)

# Example line protocol (single request aggregation point):
api_request,service=api-gateway,deployment=dev,host=localhost,version=0.5.2,method=GET,path=/v1/messages,protocol=HTTP,category=chat,status_class=2xx \
  status_code_i=200i,latency_ms_f=123.4,request_body_b=false,response_size_i=2048i 2025-08-04T07:42:53.123Z


###############################################################################
# Measurement: model_inference
#
# Replaces: otel_model_inferences
# Source:   OTel metrics from modelservice.core.metrics
###############################################################################

# Tags:
# - service       : "modelservice" (default)
# - deployment    : env/mode
# - host          : hostname
# - model_name    : logical model identifier (llama-3.2-3b, emotion-net, etc.)
# - task_type     : completion, chat, chat_streaming, embedding, sentiment, ner, ...
# - provider      : underlying provider (ollama, openai, local, etc.)

# Fields:
# - duration_ms_f       : average inference time (ms) for the exported interval
# - tokens_generated_i  : output tokens (if known)
# - prompt_tokens_i     : input tokens (if known)
# - entities_count_i    : number of extracted entities (NER)
# - entity_types_s      : comma-separated entity types (NER)
# - confidence_score_f  : confidence score for classification/sentiment
# - sentiment_result_s  : sentiment label (positive, neutral, negative, ...)
# - ttft_ms_f           : time-to-first-token in ms (LLM streaming)
# - success_b           : whether inference succeeded
# - error_message_s     : short error class / reason (optional, redacted)

# Example line protocol:
model_inference,service=modelservice,deployment=dev,host=localhost,version=0.5.2,model_name=llama-3.2-3b,task_type=chat,provider=ollama \
  duration_ms_f=842.7,tokens_generated_i=256i,prompt_tokens_i=128i,ttft_ms_f=120.5,success_b=true 2025-08-04T07:42:54.001Z

# Example with NER and sentiment fields:
model_inference,service=modelservice,deployment=dev,host=localhost,version=0.5.2,model_name=ner-en,task_type=ner,provider=local \
  duration_ms_f=45.3,entities_count_i=12i,entity_types_s="PERSON,ORG,LOC",confidence_score_f=0.94,sentiment_result_s="neutral",success_b=true 2025-08-04T07:42:55.250Z


###############################################################################
# Measurement: memory_query
#
# Replaces: otel_memory_queries
###############################################################################

# Tags:
# - service       : "backend" (or specific memory service)
# - deployment    : env/mode
# - host          : hostname
# - query_type    : semantic category (vector_search, key_lookup, timeline, ...)

# Fields:
# - query_time_ms_f   : average query duration (ms)
# - results_count_i   : number of results returned
# - success_b         : success flag

# Example line protocol:
memory_query,service=backend,deployment=dev,host=localhost,query_type=vector_search \
  query_time_ms_f=32.8,results_count_i=15i,success_b=true 2025-08-04T07:42:56.000Z


###############################################################################
# Measurement: scheduler_job
#
# Replaces: otel_scheduler_jobs
###############################################################################

# Tags:
# - service       : scheduler owner (backend, modelservice, etc.)
# - deployment    : env/mode
# - host          : hostname
# - job_type      : logical job name (nightly_cleanup, reflection_run, ...)
# - queue_name    : queue/channel name (default, high_priority, ...)

# Fields:
# - duration_ms_f   : job execution duration (ms)
# - success_b       : success flag
# - error_message_s : short error description if failed

# Example line protocol:
scheduler_job,service=backend,deployment=dev,host=localhost,job_type=reflection_run,queue_name=default \
  duration_ms_f=5034.2,success_b=true 2025-08-04T07:43:00.000Z


###############################################################################
# Measurement: messagebus_event
#
# Replaces: otel_message_bus_events
###############################################################################

# Tags:
# - service       : owning service (backend, modelservice, gateway, ...)
# - deployment    : env/mode
# - host          : hostname
# - topic         : ZeroMQ / message-bus topic (normalized)

# Fields:
# - message_count_i      : number of messages processed in the export interval
# - processing_time_ms_f : average processing time per message (ms)
# - backlog_depth_i      : reported backlog depth at export time
# - consumer_count_i     : number of active consumers

# Example line protocol:
messagebus_event,service=backend,deployment=dev,host=localhost,topic=conversation.incoming \
  message_count_i=128i,processing_time_ms_f=12.3,backlog_depth_i=5i,consumer_count_i=3i 2025-08-04T07:43:05.000Z


###############################################################################
# Future Telemetry: generic telemetry events
#
# In addition to the metric-oriented measurements above, the Telemetry
# Architecture describes a generic, JSON-centric telemetry event stream. Once
# implemented, a `telemetry_event` measurement can mirror the `telemetry` table
# in libSQL, with:
#   - category, subcategory, component, event, level as tags
#   - JSON payloads stored either as a string field or projected into
#     structured fields for key metrics.
#
# That evolution is intentionally deferred until the telemetry collector and
# message-bus integration are fully implemented.
###############################################################################
