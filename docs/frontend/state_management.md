---
title: State Management Specification
---

# State Management Specification

## Overview

AICO uses BLoC pattern with HydratedBloc for automatic state persistence and get_it for dependency injection. This provides reactive, testable state management supporting offline-first operation and cross-device synchronization.

## Architecture

### Core Components
- **BLoCs**: Handle state transitions through events and states
- **Cubits**: Simplified state management for straightforward cases
- **HydratedBloc**: Automatic state persistence to local storage
- **get_it**: Service locator managing object lifecycles and dependencies

## State Categories

### Application State (Global)

#### ConnectionBloc
Manages backend connectivity with states: Connected, Connecting, Disconnected, Offline. Persists connection preferences, backend configuration, and network failure patterns for intelligent retry logic.

#### SettingsBloc  
Handles user preferences including theme, locale, notifications, voice settings, privacy controls, and accessibility options. Full state persistence ensures settings survive app restarts.

### Feature State (Domain-Specific)

#### ConversationBloc
Manages conversation state including message history, draft messages, typing indicators, and suggested responses. Persists recent conversations and drafts for continuity across sessions.

#### AvatarBloc
Controls avatar expressions, animations, and emotional states. Persists customization preferences while maintaining real-time interaction responsiveness.

#### RelationshipBloc
Tracks family member relationships, interaction history, and relationship insights. Maintains persistent relationship data while supporting dynamic interaction updates.

### UI State (Ephemeral)

#### NavigationCubit
Manages current route, parameters, navigation history, and back button state. Only navigation preferences are persisted.

#### UiStateCubit
Handles transient UI elements like drawer state, active modals, expanded sections, and scroll positions. No persistence required.

## State Persistence

### HydratedBloc Implementation
Automatic state persistence through `fromJson()` and `toJson()` methods with graceful error handling for migration and corruption scenarios.

### Storage Hierarchy
1. **Critical State**: Always persisted (settings, connection preferences)
2. **Important State**: Size-limited persistence (conversation history)
3. **Cache State**: Temporary persistence (UI preferences)
4. **Ephemeral State**: Never persisted (loading states, animations)

### Synchronization Strategy
- **Local-First**: Immediate local updates with background sync
- **Conflict Resolution**: Last-write-wins with user notification
- **Offline Queue**: Actions queued when disconnected
- **Cross-Device Sync**: Settings and conversations across trusted devices

## Lifecycle Management

### Dependency Registration
Repositories registered as lazy singletons, feature BLoCs as factories for fresh instances, and global BLoCs as singletons for app-wide state.

### Widget Integration
Use `BlocProvider` for feature-specific BLoCs and `BlocConsumer` for combined state listening and UI building with side effect handling.

## Error Handling

Base state classes include loading flags, error messages, and exceptions with automatic retry for transient errors, user-initiated retry for persistent errors, and graceful degradation when features are unavailable.

## Testing & Performance

### Testing Strategy
- **Unit Testing**: BLoC testing with `blocTest` for state transitions
- **Integration Testing**: State persistence, cross-BLoC communication, and error scenarios
- **Performance Testing**: State update efficiency and memory usage

### Optimization
- **State Efficiency**: Immutable objects, selective rebuilds with `buildWhen`, state normalization
- **Persistence**: Selective persistence, compression for large objects, background persistence
- **Memory Management**: Proper BLoC disposal and lifecycle management

This specification ensures robust, performant state management supporting offline-first operation and cross-device synchronization.
