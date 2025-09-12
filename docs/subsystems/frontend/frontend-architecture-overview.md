---
title: Frontend Architecture Overview
---

# Frontend Architecture

## Overview

The AICO frontend is a Flutter application implementing a **thin client architecture** that prioritizes user experience through responsive interfaces and seamless backend integration. The architecture emphasizes clean separation of concerns, reactive state management with automatic persistence, and robust offline capabilities.

The frontend serves as a presentation layer that delegates all heavy processing to the backend service while maintaining rich interactivity and real-time responsiveness. This design ensures the UI remains fluid even during complex AI operations and enables the application to function gracefully when connectivity is intermittent.

## Core Design Paradigms

### 🌐 Offline-First
The application assumes network connectivity is unreliable and designs for offline operation as the default case. Local state persistence, optimistic updates, and graceful degradation ensure users can continue working regardless of backend availability.

### 📱 Thin Client
The frontend contains minimal business logic, focusing entirely on presentation and user interaction. All AI processing, data persistence, and complex operations occur in the backend service, ensuring UI responsiveness and enabling autonomous backend operation.

### ⚡ Reactive Programming
Event-driven architecture with reactive streams throughout. State changes flow unidirectionally through Riverpod StateNotifiers to UI updates, creating predictable and testable behavior that naturally handles asynchronous operations.

### 🏗️ Clean Architecture
Strict layering separates concerns: presentation layer handles UI rendering, domain layer contains business rules and entities, data layer manages external communication and storage. Dependencies point inward for testability and maintainability.

### ♿ Accessibility-First
WCAG 2.1 AA standards implemented from the ground up, ensuring usability for users with diverse abilities through semantic markup, keyboard navigation, and screen reader support.

### 🔄 Cross-Platform Consistency
Flutter's single codebase provides identical functionality across desktop, mobile, and web platforms while respecting platform-specific UI conventions and capabilities.

### 📈 Progressive Disclosure
Information and complexity are revealed gradually based on user needs and context. Primary actions are immediately visible, while advanced features are discoverable through natural exploration. Error messages focus on user impact first, with technical details available on demand.

### 🔍 System Transparency
Users always understand what the system is doing and its current state without cognitive overload. Long-running operations show clear progress indicators, system constraints are communicated contextually, and overall system health is visible through subtle status indicators.

### 🔮 Optimistic Updates
User actions immediately update the interface for instant feedback while operations complete in the background. Failed operations are handled gracefully with clear recovery options, maintaining user confidence and workflow continuity.

## Architecture Principles

### Thin Client Design
The frontend contains minimal business logic, focusing entirely on presentation and user interaction. All AI processing, data persistence, and complex operations occur in the backend service. This separation ensures the UI remains responsive and allows the backend to operate autonomously even when the frontend is closed.

### Reactive Programming
The application uses event-driven architecture with reactive streams throughout. State changes flow unidirectionally through Riverpod StateNotifiers to UI updates, creating predictable and testable behavior. This pattern naturally handles asynchronous operations like network requests and real-time updates.

### Clean Architecture
Strict layering separates concerns: the presentation layer handles UI rendering, the domain layer contains business rules and entities, and the data layer manages external communication and storage. Dependencies point inward, making the architecture testable and maintainable.

### Offline-First Design
The application assumes network connectivity is unreliable and designs for offline operation as the default case. Local state persistence, optimistic updates, and graceful degradation ensure users can continue working regardless of backend availability.

### Cross-Platform Consistency
Flutter's single codebase approach provides identical functionality across desktop, mobile, and web platforms while respecting platform-specific UI conventions and capabilities.

### Accessibility by Design
The application implements WCAG 2.1 AA standards from the ground up, ensuring usability for users with diverse abilities through semantic markup, keyboard navigation, and screen reader support.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Screens & Widgets  │  Riverpod State Management           │
│  - Conversation Interface │  - ConversationProvider            │
│  - Avatar Display   │  - ConnectionProvider                │
│  - Settings UI      │  - ThemeProvider                     │
│  - Admin Dashboard  │  - AuthProvider                      │
├─────────────────────────────────────────────────────────────┤
│                     Domain Layer                            │
├─────────────────────────────────────────────────────────────┤
│  Use Cases          │  Entities & Models                   │
│  - SendMessage      │  - Message                           │
│  - ConnectBackend   │  - User                              │
│  - ManageSettings   │  - ConnectionState                   │
│  - HandleUpdates    │  - SystemStatus                      │
├─────────────────────────────────────────────────────────────┤
│                      Data Layer                             │
├─────────────────────────────────────────────────────────────┤
│  Repositories       │  Data Sources                        │
│  - ConversationRepository │  - REST API Client               │
│  - UserRepository   │  - WebSocket Client                  │
│  - ConfigRepository │  - Local Storage                     │
│                     │  - Secure Storage                    │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### State Management (Riverpod Pattern)

The application uses **Riverpod** for all state management, providing a reactive and testable architecture. StateNotifiers act as intermediaries between the UI and data layers, managing state changes through immutable state objects and automatic UI updates.

**Reactive Flow**: User interactions trigger methods on StateNotifiers that process operations asynchronously, potentially involving API calls or local operations, before updating state that automatically rebuilds consuming widgets.

**State Persistence**: Critical state is persisted through secure storage and shared preferences, with automatic restoration on app restart.

**Currently Implemented Providers**:
- **AuthProvider**: Manages user authentication state and JWT token lifecycle
- **ConversationProvider**: Handles conversation state, message sending/receiving, and real-time updates
- **ThemeProvider**: Manages theme selection, dark/light mode, and accessibility settings
- **NetworkingProviders**: Provides unified API clients, token management, connection services, and resilient operations
- **ConnectionManager**: Core service managing connection health, retry logic, and protocol fallback
- **UnifiedConnectionStatus**: Avatar-centric immersive status system replacing legacy banner components

**Provider Architecture Benefits**:
- **Compile-time Safety**: Dependencies are checked at compile time
- **Automatic Disposal**: Riverpod handles lifecycle management automatically
- **Easy Testing**: Simple provider overrides for testing scenarios
- **No Boilerplate**: Direct state access without event/state classes

### Dependency Injection (Riverpod Implementation)

**Current Implementation**: The application uses **Riverpod** for dependency injection, providing compile-time safety, automatic lifecycle management, and easy testing capabilities.

**Riverpod Benefits Over Service Locator**:
- **Compile-time Safety**: Dependencies are checked at compile time, preventing runtime errors
- **No Hidden Dependencies**: All dependencies are explicitly declared in provider definitions
- **Automatic Disposal**: Riverpod handles resource cleanup automatically
- **Easy Testing**: Simple provider overrides for testing scenarios
- **No Async Registration**: Providers are created on-demand, eliminating timing issues
- **Circular Dependency Prevention**: Compile-time detection prevents circular dependencies

**Current Riverpod Implementation**:

```dart
// Domain layer - Abstract repository interfaces
abstract class AuthRepository {
  Future<User> login(String email, String password);
  Future<void> logout();
  Stream<AuthState> get authStateStream;
}

// Data layer - Repository implementation
class AuthRepositoryImpl implements AuthRepository {
  final ApiService _apiService;
  final TokenManager _tokenManager;
  
  AuthRepositoryImpl(this._apiService, this._tokenManager);
  // Implementation...
}

// Riverpod providers - Clean dependency injection
final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService(baseUrl: 'http://localhost:8771/api/v1');
});

final tokenManagerProvider = Provider<TokenManager>((ref) {
  return TokenManager();
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepositoryImpl(
    ref.read(apiServiceProvider),
    ref.read(tokenManagerProvider),
  );
});

// Use case layer
final loginUseCaseProvider = Provider<LoginUseCase>((ref) {
  return LoginUseCase(ref.read(authRepositoryProvider));
});

// Presentation layer - StateNotifier with clean dependencies
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    ref.read(loginUseCaseProvider),
    ref.read(autoLoginUseCaseProvider),
    ref.read(logoutUseCaseProvider),
    ref.read(checkAuthStatusUseCaseProvider),
    ref.read(tokenManagerProvider),
  );
});
```

**Key Benefits of Riverpod Approach**:
- **Compile-time safety**: Dependencies are checked at compile time
- **No service locator**: Dependencies are explicitly injected, not hidden
- **Automatic disposal**: Riverpod handles lifecycle management automatically
- **Easy testing**: Simple to override providers for testing
- **No async registration complexity**: Providers are created on-demand
- **Circular dependency prevention**: Compile-time detection of circular dependencies
- **State management integration**: Seamless integration with state management

**Architecture Layers with Riverpod**:
1. **Domain Layer**: Defines abstract interfaces and business entities
2. **Data Layer**: Implements domain interfaces with concrete data sources  
3. **Use Case Layer**: Encapsulates business logic in single-responsibility classes
4. **Presentation Layer**: StateNotifiers depend only on use cases through provider injection

**Testing Benefits**: Riverpod's provider overrides make testing trivial - simply override providers with mocks during testing without complex setup or teardown.

**Example Provider Override for Testing**:
```dart
testWidgets('auth flow test', (tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        authRepositoryProvider.overrideWithValue(mockAuthRepository),
        tokenManagerProvider.overrideWithValue(mockTokenManager),
      ],
      child: MyApp(),
    ),
  );
  // Test implementation...
});
```

### Navigation Architecture

The application implements declarative routing using `go_router`, providing type-safe navigation with deep linking support and browser-friendly URLs for web deployment.

**Declarative Routes**: Routes are defined as a configuration tree rather than imperative navigation calls, making the navigation structure clear and maintainable.

**Deep Linking**: All screens support direct URL access, enabling bookmarking, sharing, and browser navigation patterns even in desktop and mobile contexts.

**State Preservation**: Navigation maintains widget state appropriately, preserving scroll positions and form data when users navigate between screens.

### API Integration

The frontend communicates with the backend through a **UnifiedApiClient** that provides intelligent routing between encrypted and unencrypted endpoints using **JSON serialization** for all external communication:

- **REST API**: Primary communication via Dio HTTP client with automatic token refresh and interceptor-based authentication
- **HTTP Fallback**: Secondary HTTP client using the `http` package for reliability
- **WebSocket**: Basic real-time communication (limited implementation)
- **Encryption Layer**: Automatic E2E encryption for sensitive endpoints with handshake protocol

**Current Protocol Status**:
- ✅ **REST/HTTP**: Fully implemented with dual client approach
- ⚠️ **WebSocket**: Basic implementation, limited functionality
- ❌ **ZeroMQ IPC**: Not yet implemented (planned for future)

**Protocol Clarification**: The frontend exclusively uses JSON for all backend communication. Protocol Buffers are used internally within the backend modules but are not exposed to the frontend layer.

```dart
// API Client example - JSON serialization
class ApiClient {
  final String baseUrl;
  final Dio _dio;

  ApiClient(this.baseUrl) : _dio = Dio(BaseOptions(
    baseURL: baseUrl,
    contentType: 'application/json',
    responseType: ResponseType.json,
  ));

  Future<Response> post(String path, {Map<String, dynamic>? data}) {
    // Automatic JSON serialization
    return _dio.post(path, data: data);
  }

  Future<Response> get(String path, {Map<String, String>? queryParameters}) {
    // JSON response deserialization
    return _dio.get(path, queryParameters: queryParameters);
  }
}
```

```dart
// WebSocket Client example - JSON message format
class WebSocketClient {
  IOWebSocketChannel? _channel;
  final String url;
  final StreamController<Map<String, dynamic>> _messageController = 
      StreamController.broadcast();

  Stream<Map<String, dynamic>> get messages => _messageController.stream;

  void connect() {
    _channel = IOWebSocketChannel.connect(url);
    _channel!.stream.listen((data) {
      // All WebSocket messages use JSON format
      final message = json.decode(data) as Map<String, dynamic>;
      _messageController.add(message);
    });
  }

  void sendMessage(Map<String, dynamic> message) {
    if (_channel != null) {
      // JSON encoding for all outbound messages
      _channel!.sink.add(json.encode(message));
    }
  }
}
```

### Data Layer Architecture

#### API Client (REST + WebSocket)

The data layer implements the Repository pattern with abstract interfaces, separating the domain logic from specific API implementations and enabling easy testing and future backend changes.

**Dual Protocol Support**: Repositories coordinate between REST APIs for commands and queries, and WebSocket connections for real-time updates and notifications.

**Abstract Interfaces**: Domain layer depends only on repository abstractions, not concrete implementations, following dependency inversion principles.

**Error Handling**: Repositories handle network errors, timeouts, and connectivity issues, providing consistent error semantics to the business logic layer.

#### Local Storage Strategy

- **Secure Storage**: User credentials, API tokens
- **Shared Preferences**: App settings, theme preferences
- **SQLite**: Message cache, offline data
- **File Storage**: Avatar assets, temporary files

### UI Architecture

#### Design System

The UI follows atomic design principles, building complex interfaces from simple, reusable components. This approach ensures consistency, reduces code duplication, and simplifies maintenance.

**Atomic Hierarchy**: Components are organized in five levels of increasing complexity:

**Atoms**: Basic UI elements like buttons, text fields, and icons that cannot be broken down further while maintaining their function.

**Molecules**: Simple component groups that combine atoms into functional units, such as search bars or message bubbles.

**Organisms**: Complex components that combine molecules and atoms into distinct interface sections, like conversation interfaces or navigation panels.

**Templates**: Layout structures that define page-level organization without specific content, establishing consistent spacing and arrangement patterns.

**Pages**: Complete screens that populate templates with real content and connect to application state.

**Design Tokens**: Consistent spacing, typography, and color systems ensure visual coherence across all components and support dynamic theming.

#### Theme Management

The application implements Material 3 design system with dynamic theming capabilities, supporting both light and dark modes with automatic system preference detection.

**Dynamic Color**: Themes generate from seed colors using Material 3's color algorithms, ensuring harmonious color relationships and accessibility compliance.

**System Integration**: Theme selection respects system preferences by default while allowing user override, providing familiar behavior across platforms.

**Accessibility**: All color combinations meet WCAG contrast requirements, and themes support high contrast modes for improved visibility.

### WebView Integration (Avatar System)

The avatar system integrates web-based 3D rendering through a WebView component with bidirectional JavaScript communication, enabling sophisticated avatar animations while maintaining Flutter's native performance.

**JavaScript Bridge**: Custom communication channels allow Flutter to control avatar animations and receive interaction events, creating seamless integration between native UI and web-based 3D content.

**Performance Optimization**: WebView lifecycle management ensures efficient memory usage, with avatar rendering paused during background states and optimized for different device capabilities.

**Cross-Platform Rendering**: The WebView approach provides consistent avatar behavior across all Flutter platforms while leveraging mature web-based 3D libraries.

## Communication Patterns

### Backend Communication

**REST API**: Standard HTTP requests handle commands, queries, and configuration operations. The REST interface provides reliable request-response patterns for operations that require confirmation and error handling.

**WebSocket**: Real-time bidirectional communication enables live updates, notifications, and streaming responses. WebSocket connections automatically reconnect on failure and handle message queuing during disconnection periods.

**Protocol Coordination**: The communication layer intelligently routes operations to appropriate protocols - REST for stateful operations requiring confirmation, WebSocket for real-time updates and streaming data.

**Connection Management**: Automatic connection pooling, retry logic, and graceful degradation ensure reliable communication even under poor network conditions.

### Error Handling Strategy

Centralized error handling provides consistent user experience across all application features, transforming technical errors into actionable user guidance.

**Error Classification**: The system categorizes errors by type (network, validation, permission) and severity (recoverable, user action required, critical), enabling appropriate response strategies.

**User Communication**: Error messages focus on user impact and available actions rather than technical details, with progressive disclosure for users who need more information.

**Recovery Mechanisms**: Automatic retry logic handles transient failures, while persistent errors trigger user notifications with clear resolution steps.

**Error Boundaries**: UI components implement error boundaries to prevent cascading failures, ensuring that errors in one feature don't crash the entire application.

## Offline Capabilities

### Connection Management

Robust connection management ensures the application remains functional regardless of network conditions, with intelligent reconnection strategies and immersive user communication about connectivity status.

**State Monitoring**: The `ConnectionManager` continuously monitors backend connectivity using `InternalConnectionStatus` enum (connected, connecting, disconnected, offline, error) and provides real-time status updates through reactive streams.

**Reconnection Strategy**: Exponential backoff algorithms with jitter prevent overwhelming the backend during outages while ensuring prompt reconnection when service resumes. Protocol fallback (WebSocket → HTTP) provides additional resilience.

**Immersive Status Feedback**: Connection status is communicated through an avatar-centric system using dynamic rings, ambient effects, and contextual hints. This approach eliminates intrusive banners while providing clear visual feedback about system health:
- **Emerald rings**: Connected and healthy
- **Sapphire rings**: Connecting or syncing
- **Amber rings**: Degraded connectivity or authentication required
- **Coral rings**: Disconnected or error states
- **Ambient particles**: Celebration effects during reconnection
- **Contextual hints**: Minimal text guidance only when user action is required

**Unified Architecture**: The system uses a single `UnifiedConnectionStatus` widget that wraps screens and coordinates between the `ConnectionManager` service layer and the immersive UI presentation, eliminating legacy banner systems and duplicate status components.

### Data Synchronization

Optimistic updates provide immediate user feedback while ensuring data consistency through robust conflict resolution and retry mechanisms.

**Optimistic Updates**: User actions immediately update the local interface, providing instant feedback while the actual operation completes in the background.

**Conflict Resolution**: When local and remote state diverge, the system applies consistent resolution strategies, typically favoring the most recent change while preserving user intent.

**Retry Logic**: Failed operations automatically retry with exponential backoff, and users can manually retry operations that require their attention.

**State Reconciliation**: Periodic synchronization ensures local state remains consistent with the backend, resolving any discrepancies that may arise from network issues or concurrent modifications.

## Performance Optimization

### Memory Management

- **Widget Recycling**: ListView.builder for large message lists
- **Image Caching**: Cached network images with size limits
- **Stream Disposal**: Proper subscription cleanup in BLoCs

### Rendering Optimization

- **Const Constructors**: Immutable widgets where possible
- **RepaintBoundary**: Isolate expensive repaints
- **AutomaticKeepAlive**: Preserve state for tab views

### Asset Management

- **Vector Graphics**: SVG icons for scalability
- **Image Optimization**: WebP format with fallbacks
- **Font Subsetting**: Reduced font file sizes

## Security Considerations

### Data Protection

- **Secure Storage**: Encrypted local storage for sensitive data
- **Certificate Pinning**: SSL/TLS security for API calls
- **Input Validation**: Client-side validation with server verification

### Privacy Features

- **Biometric Authentication**: Optional biometric unlock
- **Screen Recording Protection**: Prevent sensitive data capture
- **Secure Keyboard**: Protected text input for passwords

## Testing Strategy

### Unit Tests
- **BLoC Testing**: State transitions and event handling
- **Repository Testing**: Data layer logic
- **Utility Testing**: Helper functions and extensions

### Widget Tests
- **Component Testing**: Individual widget behavior
- **Integration Testing**: Widget interaction flows
- **Golden Tests**: Visual regression testing

### Integration Tests
- **End-to-End**: Complete user journeys
- **API Integration**: Backend communication
- **Performance Testing**: Memory and rendering benchmarks

## Development Workflow

### Code Organization

**Legacy Implementation Structure (Problematic)**:
```
lib/
├── core/
│   ├── di/              # ❌ Service Locator anti-pattern
│   └── ...
├── networking/          # ❌ Mixed data/domain concerns
├── presentation/        # ❌ Tight coupling to concrete implementations
└── main.dart
```

**Modern 2025 Clean Architecture Structure**:

Following Flutter community best practices and Clean Architecture principles:

```
lib/
├── domain/                    # 🏗️ Business Logic Layer (Pure Dart)
│   ├── entities/             # Core business objects (User, Message, etc.)
│   ├── repositories/         # Abstract repository interfaces
│   ├── usecases/            # Single-responsibility business logic
│   └── failures/            # Domain-specific error types
├── data/                     # 📊 Data Access Layer
│   ├── datasources/         # Abstract data source interfaces
│   │   ├── remote/          # API data sources
│   │   └── local/           # Local storage data sources
│   ├── models/              # Data models with JSON serialization
│   ├── repositories/        # Repository implementations
│   └── providers/           # Riverpod data providers
├── presentation/             # 🎨 Presentation Layer
│   ├── providers/           # Riverpod state providers
│   ├── screens/             # Application screens
│   ├── widgets/             # Reusable UI components
│   └── theme/               # Theme and styling
├── core/                     # 🔧 Infrastructure Layer
│   ├── constants/           # App constants
│   ├── errors/              # Error handling utilities
│   ├── network/             # Network utilities (Dio setup)
│   ├── storage/             # Storage utilities
│   ├── utils/               # Helper functions
│   └── providers.dart       # Core Riverpod providers
├── shared/                   # 🤝 Shared Components
│   ├── widgets/             # Cross-feature widgets
│   └── extensions/          # Dart extensions
└── main.dart                # Application entry point
```

**Key Architectural Improvements**:

1. **Pure Domain Layer**: Contains only business logic, no external dependencies
2. **Clear Separation**: Each layer has distinct responsibilities
3. **Dependency Inversion**: Higher layers depend on abstractions, not concretions
4. **Riverpod Integration**: Modern dependency injection throughout
5. **Feature-First Option**: Can be organized by features for larger teams

**Alternative Feature-First Structure** (for large teams):
```
lib/
├── features/
│   ├── authentication/
│   │   ├── domain/
│   │   ├── data/
│   │   └── presentation/
│   ├── conversation/
│   │   ├── domain/
│   │   ├── data/
│   │   └── presentation/
│   └── settings/
│       ├── domain/
│       ├── data/
│       └── presentation/
├── core/                    # Shared infrastructure
└── shared/                  # Shared components
```

### Build Configuration

- **Flavors**: Development, staging, production environments
- **Code Generation**: JSON serialization, route generation
- **Asset Generation**: Icon and splash screen automation

## Platform-Specific Features

### Desktop Integration
- **Window Management**: Minimize to system tray
- **Keyboard Shortcuts**: Global hotkeys for quick access
- **File System**: Drag-and-drop file handling

### Mobile Optimization
- **Background Processing**: Limited background tasks
- **Push Notifications**: Local notifications for updates
- **Adaptive UI**: Platform-specific navigation patterns

### Web Deployment
- **Progressive Web App**: Offline capability and installation
- **WASM Integration**: High-performance computations
- **Browser API**: File system access and notifications

## Monitoring and Analytics

### Performance Monitoring
- **Flutter Inspector**: Debug widget tree and performance
- **Timeline Events**: Custom performance markers
- **Memory Profiling**: Heap analysis and leak detection

### Error Tracking
- **Crash Reporting**: Automated crash collection
- **User Feedback**: In-app feedback collection
- **Analytics**: Usage patterns and feature adoption

This architecture ensures a maintainable, scalable, and performant Flutter application that provides an excellent user experience while maintaining clean separation of concerns and professional development practices.
