# AICO Gateway

## Purpose

The Gateway is the HTTP/WebSocket entry point for all client requests to the AICO system. It handles:

- **Authentication & Authorization** - JWT validation, user session management
- **Request Routing** - Proxies requests to Core via NATS
- **WebSocket Management** - Real-time conversation streaming
- **Rate Limiting** - Request throttling and abuse prevention
- **API Documentation** - OpenAPI/Swagger endpoints

## Architecture

```
Client (Studio/CLI)
    ↓ HTTP/WebSocket
Gateway (FastAPI)
    ↓ NATS Request/Reply
Core (Business Logic)
```

## Key Components

### `/api`
- **`/operations/router.py`** - Operations endpoints (topology, backups, databases)
- **`dependencies.py`** - Authentication dependencies (JWT validation, user extraction)
- **`errors.py`** - HTTP error handling

### `/adapters`
- NATS client adapters for Core communication

### `/core`
- Gateway-specific core logic (NATS client management)

### `/middleware`
- Authentication middleware
- CORS configuration
- Request logging

## Running

```bash
# Development
cd gateway
python -m gateway.main

# Docker
docker compose up aico-gateway
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Token refresh

### Operations (Admin)
- `GET /api/operations/topology` - System topology
- `GET /api/operations/backup-sets` - List backups
- `POST /api/operations/backup-sets` - Create backup

### Conversations
- `WebSocket /ws/conversation` - Real-time conversation streaming

## Environment Variables

```bash
NATS_URL=nats://localhost:4222
JWT_SECRET_KEY=<secret>
JWT_ALGORITHM=HS256
GATEWAY_PORT=8771
```

## Dependencies

- **FastAPI** - Web framework
- **NATS** - Message bus client
- **python-jose** - JWT handling
- **passlib** - Password hashing
- **httpx** - HTTP client for health checks

## Architecture Principles

1. **Stateless** - No business logic, pure routing layer
2. **Authentication Only** - Authorization decisions delegated to Core
3. **NATS-First** - All Core communication via NATS (no direct HTTP)
4. **Fail Fast** - Quick validation, detailed errors
5. **Observable** - Comprehensive logging and tracing
