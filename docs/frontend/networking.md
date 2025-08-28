# AICO Frontend Networking Client

## Architecture Overview

AICO's networking client provides a unified interface for communicating with the backend API Gateway across multiple protocols. The architecture prioritizes type safety, maintainability, and offline-first user experience while supporting REST, WebSocket, and future IPC communication.

The design follows a **layered approach** where high-level repositories abstract protocol details from business logic, while specialized clients handle the technical aspects of each communication method. This separation ensures the UI layer remains protocol-agnostic and testable.

## Core Structure

The networking layer is organized into focused modules within `lib/networking/`:

- **Clients**: Protocol-specific implementations (REST, WebSocket, IPC)
- **Interceptors**: Cross-cutting concerns like authentication and retry logic  
- **Models**: Shared data structures and error handling
- **Services**: Higher-level coordination like connection management and offline queuing

```
lib/networking/
├── clients/          # Protocol implementations
├── interceptors/     # Cross-cutting concerns
├── models/          # Shared data structures
└── services/        # Coordination layer
```

## REST API Client

The REST client uses **Retrofit** to generate type-safe API interfaces from annotations. This approach eliminates boilerplate while providing compile-time safety and excellent IDE support. Retrofit builds on **Dio**, which handles the underlying HTTP communication with advanced features like connection pooling and request/response transformation.

Key benefits include automatic serialization, declarative endpoint definitions, and seamless integration with Flutter's async/await patterns. The generated client handles all HTTP details while exposing clean, typed methods to the repository layer.

```dart
@RestApi(baseUrl: "http://localhost:8771/api/v1")
abstract class AicoApiClient {
  // Generated factory constructor
  factory AicoApiClient(Dio dio, {String baseUrl}) = _AicoApiClient;

  @GET("/users")
  Future<UserListResponse> getUsers({@Query("user_type") String? userType});
}
```

## WebSocket Client

WebSocket communication enables real-time features like live updates and bidirectional messaging. The client manages connection lifecycle, automatic reconnection, and message queuing during disconnections.

The implementation uses `IOWebSocketChannel` for robust connection handling and maintains an internal message queue to ensure no data is lost during temporary network issues. Messages are JSON-encoded for consistency with the REST API format.

Connection resilience is critical for user experience - the client automatically attempts reconnection with exponential backoff and queues outgoing messages until the connection is restored.

## Connection Management

The connection manager provides **adaptive transport selection** that automatically chooses the best available protocol based on network conditions and server availability. This ensures optimal performance while maintaining reliability through graceful degradation.

The system follows a preference hierarchy: IPC for local high-performance scenarios, WebSocket for real-time features, and HTTP as the reliable fallback. When a connection fails, the manager automatically attempts the next protocol without user intervention.

This approach abstracts transport complexity from the application layer - repositories and business logic remain unchanged regardless of the underlying protocol.
```

## Authentication & Security

Authentication is handled transparently through **interceptors** that automatically attach JWT tokens to outgoing requests. The system manages token lifecycle including automatic refresh when tokens expire, ensuring users never experience authentication interruptions.

When a token expires during a request, the interceptor automatically attempts to refresh it and retries the original request seamlessly. This provides a smooth user experience while maintaining security through short-lived tokens.

All authentication state is managed centrally, with secure token storage following platform best practices. The interceptor pattern ensures authentication logic is applied consistently across all API calls without requiring manual token management in business logic.
```

## Repository Pattern

The **repository pattern** provides a clean abstraction between business logic and network implementation. Repositories define domain-focused interfaces that hide protocol complexity, making the codebase more maintainable and testable.

Each repository handles data operations for a specific domain (users, admin, health) and can switch between different transport protocols transparently. This separation allows the UI layer to work with domain objects rather than network responses.

Repositories also coordinate **offline-first behavior** by implementing optimistic updates and operation queuing. When network requests fail, operations are queued for later execution while providing immediate feedback to users through optimistic UI updates.
```

## Offline-First Architecture

The networking client prioritizes **user experience over network reliability** through comprehensive offline support. When network operations fail, the system provides immediate optimistic feedback while queuing operations for background execution.

Operations are persisted locally and automatically retried when connectivity returns. This ensures users can continue working seamlessly regardless of network conditions, with changes synchronized transparently in the background.

The offline queue implements intelligent retry logic with exponential backoff and conflict resolution. Failed operations are preserved across app restarts, ensuring no user data is lost due to temporary network issues.
```

## Implementation Phases

1. **Phase 1**: REST API client with Retrofit + Dio
2. **Phase 2**: WebSocket client for real-time features  
3. **Phase 3**: Connection management and protocol fallback
4. **Phase 4**: Offline queue and optimistic updates
5. **Phase 5**: IPC client for local high-performance scenarios

## Key Benefits

- **Type Safety**: Compile-time safe API clients via code generation
- **Maintainability**: Clean separation between protocols and business logic
- **Testability**: Abstract interfaces enable easy mocking
- **Offline-First**: Optimistic updates with operation queueing
- **Resilience**: Comprehensive retry and fallback mechanisms
- **Performance**: Advanced HTTP features (connection pooling, interceptors)
