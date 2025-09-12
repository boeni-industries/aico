---
title: State Management Specification
---

# State Management Specification

## Overview

AICO uses **Riverpod** with StateNotifier pattern for reactive state management and dependency injection. This provides compile-time safe, testable state management supporting offline-first operation and automatic lifecycle management.

## Architecture

### Core Components
- **StateNotifiers**: Handle state transitions through immutable state objects
- **Providers**: Dependency injection and state access with compile-time safety
- **Secure Storage**: Persistent storage for critical state (auth tokens, user preferences)
- **Shared Preferences**: Non-sensitive settings and UI preferences

## State Categories

### Application State (Global)

#### AuthProvider (StateNotifier)
Manages user authentication state including login/logout, token refresh, and auto-login. Persists authentication state through secure storage with automatic token lifecycle management.

#### ThemeProvider (StateNotifier)
Handles user preferences including theme mode (light/dark/system), high contrast settings, and accessibility options. State persistence through shared preferences ensures settings survive app restarts.

### Feature State (Domain-Specific)

#### ConversationProvider (StateNotifier)
Manages conversation state including message history, sending/receiving messages, loading states, and error handling. Integrates with backend API for real-time conversation updates and optimistic UI updates.

#### ConnectionProvider (Planned)
Will handle backend connectivity monitoring, automatic reconnection, and offline mode detection. Will provide connection status to other providers for graceful degradation.

#### SettingsProvider (Planned)
Will manage application settings, user preferences, and configuration options with automatic persistence and validation.

### UI State (Ephemeral)

#### Navigation State
Managed through go_router with declarative routing. Navigation state is automatically managed by the router with deep linking support.

#### UI State
Transient UI elements like loading states, modal visibility, and form validation are managed locally within widgets or through temporary providers that don't require persistence.

## State Persistence

### Riverpod Persistence Strategy
State persistence through platform-specific secure storage and shared preferences, with automatic restoration on app startup.

### Storage Hierarchy
1. **Critical State**: Secure storage (JWT tokens, user credentials, encryption keys)
2. **User Preferences**: Shared preferences (theme settings, app configuration)
3. **Cache State**: Memory-only providers (API responses, temporary UI state)
4. **Ephemeral State**: Widget-local state (loading indicators, form validation)

### Synchronization Strategy
- **Optimistic Updates**: Immediate UI updates with background API calls
- **Error Recovery**: Automatic retry with exponential backoff for failed operations
- **State Reconciliation**: Periodic sync with backend to resolve any inconsistencies
- **Offline Support**: Local state management with sync when connectivity restored

## Lifecycle Management

### Provider Lifecycle
Riverpod automatically manages provider lifecycle - providers are created on first access and disposed when no longer needed. Global providers (auth, theme) persist throughout app lifecycle.

### Widget Integration
Use `ConsumerWidget` or `Consumer` for reactive UI updates. StateNotifiers automatically notify listeners when state changes, triggering widget rebuilds only for affected components.

## Error Handling

State classes include loading flags, error messages, and error types. StateNotifiers handle errors through:
- **Automatic Retry**: Exponential backoff for network errors
- **User Feedback**: Clear error messages with actionable recovery options
- **Graceful Degradation**: Fallback behavior when services are unavailable
- **Error Boundaries**: Isolated error handling prevents cascading failures

## Testing & Performance

### Testing Strategy
- **Unit Testing**: StateNotifier testing with provider overrides for isolated testing
- **Widget Testing**: Consumer widget testing with mock providers
- **Integration Testing**: End-to-end state flows and persistence scenarios
- **Provider Testing**: Dependency injection and provider lifecycle testing

### Optimization
- **State Efficiency**: Immutable state objects, selective widget rebuilds, normalized state structure
- **Provider Optimization**: Lazy loading, automatic disposal, dependency caching
- **Memory Management**: Automatic provider lifecycle management, efficient state updates
- **Performance Monitoring**: Provider rebuild tracking, state update profiling

## Current Implementation Status

### ✅ Implemented
- **AuthProvider**: Complete authentication state management with token lifecycle
- **ConversationProvider**: Full conversation state with message sending/receiving
- **ThemeProvider**: Theme management with system preference detection
- **Core Providers**: Networking, storage, and utility providers

### 🚧 In Progress
- **Connection Monitoring**: Backend connectivity status and offline detection
- **Settings Management**: Comprehensive app settings and user preferences
- **Error Recovery**: Enhanced error handling and retry mechanisms

### 📋 Planned
- **Avatar State**: Avatar animation and interaction state management
- **Notification State**: Push notification and alert management
- **Performance Monitoring**: State update metrics and optimization

This specification reflects the current Riverpod-based architecture, providing robust, performant state management with compile-time safety and automatic lifecycle management.
