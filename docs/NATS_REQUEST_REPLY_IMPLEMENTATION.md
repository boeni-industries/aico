# NATS Request/Reply Implementation for Gateway→Core Communication

## Status: 90% Complete - Needs Testing

## What Was Implemented

### 1. Core Infrastructure ✅
- **`MessageBusClient.request()`** - Added NATS request/reply method with timeout handling
  - File: `shared/aico/core/bus.py`
  - Supports timeout, returns protobuf envelope
  - Raises `MessageBusTimeoutError` on timeout

### 2. Core-Side Request Handlers ✅
- **`CoreNATSHandlers`** - Handles gateway requests in core service
  - File: `backend/core/nats_handlers.py`
  - Handlers for:
    - `scheduler/status` - Returns scheduler status
    - `scheduler/tasks` - Returns task list
    - `emotion/history` - Returns emotion history
  - Integrated into core lifecycle manager startup

### 3. Gateway-Side Client ✅
- **`GatewayNATSClient`** - Helper for gateway to make NATS requests
  - File: `backend/api_gateway/core/nats_client.py`
  - Methods:
    - `request_scheduler_status()`
    - `request_scheduler_tasks(enabled_only)`
    - `request_emotion_history(limit, hours)`

### 4. Gateway Endpoints Updated ✅
- **Scheduler endpoints** - Updated to use NATS
  - File: `backend/api/scheduler/router.py`
  - `/status` - Uses `GatewayNATSClient.request_scheduler_status()`
  - `/tasks` - Uses `GatewayNATSClient.request_scheduler_tasks()`

## What Still Needs to Be Done

### 1. Initialize Gateway NATS Client ⚠️
The `GatewayNATSClient` singleton needs to be initialized in the gateway lifecycle manager:

```python
# In backend/core/lifecycle_manager.py, gateway startup section:
from backend.api_gateway.core.nats_client import initialize_gateway_nats_client

# After message bus is available:
message_bus = self.container.get_service("message_bus")
if message_bus:
    initialize_gateway_nats_client(message_bus)
```

### 2. Complete Emotion Router Update ⚠️
The emotion history endpoint signature was updated but the implementation still needs to be changed to use NATS:

```python
# In backend/api/emotion/router.py, get_emotion_history function:
try:
    from backend.api_gateway.core.nats_client import get_gateway_nats_client
    
    nats_client = get_gateway_nats_client()
    
    # Calculate hours from days if provided
    if days:
        hours = days * 24
    elif not hours:
        hours = 24  # default
    
    history_data = await nats_client.request_emotion_history(
        limit=limit,
        hours=hours
    )
    
    return EmotionHistoryResponse(**history_data)
except Exception as e:
    logger.error(f"Failed to get emotion history: {e}")
    raise_api_error(
        status_code=500,
        error_code="EMOTION_ENGINE_UNAVAILABLE",
        message="Emotion engine unavailable"
    )
```

### 3. Fix Core Handler Bugs 🐛
The core handlers need to properly handle the emotion engine's async methods:

```python
# In backend/core/nats_handlers.py, handle_emotion_history_request:
# Change from:
history = await emotion_engine.get_history(limit=limit, hours=hours)

# To (check actual emotion engine API):
history = emotion_engine.get_recent_history(limit=limit, hours=hours)
# OR query the database directly via UoW
```

### 4. Test End-to-End 🧪
1. Rebuild containers: `cd /Users/mbo/Documents/dev/aico && docker compose -f docker/docker-compose.local.yml up --build -d gateway core`
2. Check core logs for NATS handler registration: `docker logs aico-core | grep "NATS request handlers"`
3. Check gateway logs for NATS client initialization: `docker logs aico-gateway | grep "Gateway NATS client"`
4. Test from Studio:
   - Scheduler status: Should return data instead of 503
   - Emotion history: Should return data instead of 500

## Architecture Notes

- **Gateway role**: HTTP edge, no domain services, proxies to core via NATS
- **Core role**: Domain services (scheduler, emotion engine), responds to NATS requests
- **NATS subjects**: Using dot notation (`scheduler.status`, `emotion.history`)
- **Payload format**: JSON wrapped in protobuf Struct, packed in AicoMessage envelope
- **Timeout**: 5 seconds default for all requests

## Rollback Plan

If this doesn't work, the frontend already has graceful error handling (`.catch(() => null)` on scheduler/emotion calls), so Studio will continue to work without these features.
