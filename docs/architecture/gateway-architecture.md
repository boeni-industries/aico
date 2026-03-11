# Gateway Service Architecture

## Overview

The Gateway service is the **HTTP/WebSocket edge layer** for the AICO system. It handles all external client connections, authentication, and proxies requests to the Core service via NATS messaging.

## Architectural Principles

### 1. **Thin Edge Layer**
- Gateway is stateless and lightweight
- No business logic - only routing and protocol translation
- No direct database access (uses UnitOfWork pattern via NATS)
- All business operations delegated to Core via NATS

### 2. **Protocol Adapter Pattern**
- Supports multiple protocols (REST, WebSocket, gRPC future)
- Each protocol has dedicated adapter
- Adapters translate protocol-specific requests to NATS messages

### 3. **Plugin Architecture**
- Modular middleware via plugin system
- Plugins handle cross-cutting concerns (auth, rate limiting, encryption)
- Priority-based execution order
- Hot-reloadable plugins

### 4. **Separation of Concerns**
```
Client Request
    ↓
[Protocol Adapter] ← Handles HTTP/WS specifics
    ↓
[Authentication] ← Verifies JWT, validates session
    ↓
[Authorization] ← Checks permissions
    ↓
[Message Router] ← Routes to Core via NATS
    ↓
[NATS Client] ← Request/Reply messaging
    ↓
Core Service (business logic)
```

## Core Components

### Authentication Manager

**Location**: `/gateway/middleware/auth.py`

**Responsibilities**:
- JWT token validation
- Session management (via AsyncSessionService)
- User credential verification
- Token refresh and revocation

**Pattern**: Uses existing `AsyncSessionService` from `/shared/aico/security/async_session_service.py`

**Key Methods**:
```python
async def authenticate(credentials: dict, client_info: dict) -> AuthResult
async def validate_token(token: str) -> TokenPayload
async def create_session(user_uuid: str, device_uuid: str) -> SessionInfo
async def revoke_session(session_id: str) -> bool
```

### Authorization Manager

**Location**: `/gateway/middleware/authz.py`

**Responsibilities**:
- Role-based access control (RBAC)
- Permission checking
- Resource-level authorization
- Policy enforcement

**Pattern**: Uses existing `AuthorizationService` from `/shared/aico/core/authorization.py`

**Key Methods**:
```python
async def authorize(user: dict, action: str, resource: dict) -> AuthzResult
async def check_permission(user_uuid: str, permission: str) -> bool
async def check_role(user_uuid: str, role: str) -> bool
```

### Message Router

**Location**: `/gateway/middleware/message_router.py`

**Responsibilities**:
- Routes HTTP/WS requests to appropriate NATS subjects
- Handles request/reply pattern
- Timeout management
- Error handling and retries

**Pattern**: NATS Request/Reply with subject-based routing

**Key Methods**:
```python
async def route_request(subject: str, payload: dict, timeout: float) -> dict
async def route_to_core(operation: str, data: dict) -> dict
async def subscribe_to_events(topics: list, callback: callable) -> None
```

### Protocol Adapters

#### REST Adapter
**Location**: `/gateway/adapters/rest_adapter.py`

- FastAPI integration
- OpenAPI documentation
- HTTP request/response handling
- CORS support

#### WebSocket Adapter
**Location**: `/gateway/adapters/websocket_adapter.py`

- Real-time bidirectional communication
- Connection lifecycle management
- Topic subscriptions
- Heartbeat/keepalive

## Data Flow

### REST Request Flow
```
1. Client → HTTP Request → FastAPI
2. FastAPI → Security Middleware → Auth Manager
3. Auth Manager → Validate JWT → Session Service
4. Security Middleware → Authz Manager → Check Permissions
5. Route Handler → Message Router → NATS Request
6. NATS → Core Service → Business Logic
7. Core → NATS Reply → Message Router
8. Message Router → FastAPI → HTTP Response → Client
```

### WebSocket Flow
```
1. Client → WS Connect → WebSocket Adapter
2. Client → Auth Message → Auth Manager
3. Auth Manager → Create Session → Session Service
4. Client → Subscribe Message → Authz Manager
5. Authz Manager → Check Permission → Allow/Deny
6. Client → Request Message → Message Router → NATS
7. Core → NATS Publish → Message Router → WS Send → Client
```

## Security Architecture

### Authentication Flow
1. **Login**: Client sends credentials → Auth Manager validates → Creates session → Returns JWT
2. **Request**: Client sends JWT → Auth Manager validates → Checks session → Allows/Denies
3. **Refresh**: Client sends refresh token → Auth Manager validates → Issues new JWT
4. **Logout**: Client sends logout → Auth Manager revokes session → Invalidates JWT

### Session Management
- **Storage**: PostgreSQL via AsyncSessionService
- **Lifetime**: 15 minutes (configurable)
- **Refresh**: Automatic via refresh tokens
- **Revocation**: Immediate via session invalidation

### Authorization Model
- **Roles**: Defined in `config/defaults/security.yaml`
- **Permissions**: Role-based permission sets
- **Policies**: Stored in `auth_access_policies` table
- **Wildcards**: Support for `admin.*` style permissions

## Configuration

### Gateway Configuration
**File**: `config/defaults/api_gateway.yaml`

```yaml
api_gateway:
  rest:
    host: "0.0.0.0"
    port: 3002
    cors_enabled: true
    cors_origins: ["*"]
  
  websocket:
    enabled: true
    heartbeat_interval: 30
    max_connections: 1000
  
  plugins:
    security:
      enabled: true
      jwt_expiration: 900  # 15 minutes
    
    rate_limiter:
      enabled: true
      requests_per_minute: 60
```

### NATS Configuration
**File**: `config/defaults/message_bus.yaml`

```yaml
message_bus:
  nats:
    host: "localhost"
    port: 4222
    timeout: 5.0
    max_reconnect_attempts: 10
```

## Deployment

### Docker
- **Image**: `aico-gateway`
- **Dockerfile**: `/docker/Dockerfile.gateway`
- **Dependencies**: NATS, Core service
- **Ports**: 3002 (HTTP), 3003 (WebSocket)

### Environment Variables
```bash
AICO_NATS_HOST=nats
AICO_NATS_PORT=4222
AICO_GATEWAY_PORT=3002
AICO_LOG_LEVEL=INFO
```

## Testing

### Unit Tests
```bash
cd gateway && pytest tests/unit/
```

### Integration Tests
```bash
cd gateway && pytest tests/integration/
```

### Manual Testing
```bash
# Start Gateway
cd gateway && uv run python -m gateway.main

# Test health endpoint
curl http://localhost:3002/health

# Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:3002/api/v1/conversations
```

## Monitoring

### Metrics
- Request count by endpoint
- Response times (p50, p95, p99)
- Error rates
- Active WebSocket connections
- NATS message latency

### Logging
- Structured JSON logs
- Request/response logging
- Error tracking
- Security events (auth failures, permission denials)

## Best Practices

### 1. **No Business Logic**
❌ **Wrong**: Implementing user creation logic in Gateway
```python
# gateway/api/users.py
async def create_user(user_data: dict):
    # Validate email
    # Hash password
    # Insert into database
    # Send welcome email
```

✅ **Correct**: Proxying to Core via NATS
```python
# gateway/api/users.py
async def create_user(user_data: dict):
    return await message_router.route_to_core("user.create", user_data)
```

### 2. **Stateless Design**
- No in-memory session storage
- No caching of business data
- All state in PostgreSQL or Core service

### 3. **Error Handling**
```python
try:
    result = await message_router.route_to_core("operation", data)
    return result
except TimeoutError:
    raise HTTPException(status_code=504, detail="Core service timeout")
except NATSError as e:
    raise HTTPException(status_code=503, detail="Service unavailable")
```

### 4. **Dependency Injection**
```python
# Use FastAPI dependency injection
async def get_auth_manager(request: Request) -> AuthenticationManager:
    return request.app.state.auth_manager

@router.get("/protected")
async def protected_endpoint(
    auth_manager: AuthenticationManager = Depends(get_auth_manager)
):
    # Use auth_manager
```

## Migration Notes

### From Monolithic Backend
The Gateway service was extracted from the monolithic `/backend` directory. Key changes:

1. **Removed**: All business logic, database repositories, AI services
2. **Kept**: HTTP/WS handling, authentication, protocol adapters
3. **Added**: NATS message routing, plugin system
4. **Shared**: Common utilities moved to `/shared/aico/common`

### Import Path Updates
```python
# Old (monolithic)
from backend.api.dependencies import get_current_user
from backend.core.service_container import ServiceContainer

# New (Gateway)
from gateway.api.dependencies import get_current_user
from aico.common.service_container import ServiceContainer
```

## Future Enhancements

1. **gRPC Support**: Add gRPC protocol adapter
2. **GraphQL**: GraphQL gateway for flexible queries
3. **API Versioning**: Support multiple API versions
4. **Circuit Breaker**: Prevent cascade failures
5. **Request Caching**: Cache frequent read operations
6. **Distributed Tracing**: OpenTelemetry integration
