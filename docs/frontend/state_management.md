---
title: State Management Specification
---

# State Management Specification

## Overview

AICO's frontend implements a comprehensive state management strategy using the BLoC pattern with HydratedBloc for persistence, supported by get_it for dependency injection. This approach provides reactive, testable, and persistent state management that aligns with the offline-first and thin client paradigms.

## State Management Architecture

### Core Components

#### BLoC Pattern Implementation
- **Business Logic Components (BLoCs)** handle all state transitions through events and states
- **Cubits** provide simplified state management for straightforward use cases
- **HydratedBloc** extends BLoCs with automatic state persistence
- **Event-driven architecture** ensures predictable state changes

#### Dependency Injection
- **get_it service locator** manages object lifecycles and dependencies
- **Singleton registration** for shared resources (API clients, repositories)
- **Factory registration** for stateful components (BLoCs, use cases)
- **Lazy initialization** for performance optimization

## State Categories

### 1. Application State (Global)

#### ConnectionBloc
**Purpose**: Manages backend connectivity and network state
**Persistence**: Critical state persisted via HydratedBloc

```dart
// States
abstract class ConnectionState {
  Connected({required String backendVersion, required DateTime connectedAt})
  Connecting({required int attemptCount, required Duration nextRetry})
  Disconnected({required String reason, required DateTime disconnectedAt})
  Offline({required bool hasLocalData, required DateTime lastSync})
}

// Events
abstract class ConnectionEvent {
  ConnectRequested()
  ConnectionEstablished({required BackendInfo info})
  ConnectionLost({required String reason})
  ReconnectAttempted()
  OfflineModeActivated()
}
```

**Persistence Strategy**:
- Connection preferences and settings
- Last known backend configuration
- Offline mode preferences
- Network failure patterns for intelligent retry

#### SettingsBloc
**Purpose**: Manages user preferences and application configuration
**Persistence**: Full state persistence via HydratedBloc

```dart
// State
class SettingsState {
  final ThemeMode themeMode;
  final Locale locale;
  final bool notificationsEnabled;
  final VoiceSettings voiceSettings;
  final PrivacySettings privacySettings;
  final AccessibilitySettings accessibilitySettings;
}

// Events
abstract class SettingsEvent {
  ThemeChanged({required ThemeMode theme})
  LocaleChanged({required Locale locale})
  NotificationToggled({required bool enabled})
  VoiceSettingsUpdated({required VoiceSettings settings})
  PrivacySettingsUpdated({required PrivacySettings settings})
  AccessibilitySettingsUpdated({required AccessibilitySettings settings})
  SettingsReset()
}
```

### 2. Feature State (Domain-Specific)

#### ChatBloc
**Purpose**: Manages conversation state and message handling
**Persistence**: Conversation history and draft messages

```dart
// State
class ChatState {
  final List<Message> messages;
  final String? draftMessage;
  final bool isTyping;
  final bool isAicoTyping;
  final ConversationContext context;
  final List<String> suggestedResponses;
}

// Events
abstract class ChatEvent {
  MessageSent({required String content, required MessageType type})
  MessageReceived({required Message message})
  DraftUpdated({required String draft})
  TypingStarted()
  TypingStopped()
  AicoTypingChanged({required bool isTyping})
  ConversationCleared()
  SuggestedResponseSelected({required String response})
}
```

**Persistence Strategy**:
- Recent conversation history (configurable limit)
- Draft messages for conversation continuity
- User preferences for conversation display
- Conversation context for relationship continuity

#### AvatarBloc
**Purpose**: Controls avatar state, animations, and expressions
**Persistence**: Avatar preferences and customization

```dart
// State
class AvatarState {
  final AvatarExpression currentExpression;
  final AvatarAnimation currentAnimation;
  final EmotionalState emotionalState;
  final bool isInteracting;
  final AvatarCustomization customization;
}

// Events
abstract class AvatarEvent {
  ExpressionChanged({required AvatarExpression expression})
  AnimationTriggered({required AvatarAnimation animation})
  EmotionalStateUpdated({required EmotionalState state})
  InteractionStarted()
  InteractionEnded()
  CustomizationUpdated({required AvatarCustomization customization})
}
```

#### RelationshipBloc
**Purpose**: Manages family member relationships and interactions
**Persistence**: Relationship data and interaction history

```dart
// State
class RelationshipState {
  final Map<String, FamilyMember> familyMembers;
  final String? currentActiveRelationship;
  final List<Interaction> recentInteractions;
  final RelationshipInsights insights;
}

// Events
abstract class RelationshipEvent {
  FamilyMemberAdded({required FamilyMember member})
  FamilyMemberUpdated({required String id, required FamilyMember member})
  RelationshipActivated({required String memberId})
  InteractionRecorded({required Interaction interaction})
  InsightsUpdated({required RelationshipInsights insights})
}
```

### 3. UI State (Ephemeral)

#### NavigationCubit
**Purpose**: Manages navigation state and routing
**Persistence**: Navigation preferences only

```dart
// State
class NavigationState {
  final String currentRoute;
  final Map<String, dynamic> routeParameters;
  final List<String> navigationHistory;
  final bool canGoBack;
}
```

#### UiStateCubit
**Purpose**: Manages transient UI state
**Persistence**: None (ephemeral state only)

```dart
// State
class UiState {
  final bool isDrawerOpen;
  final bool isSearchActive;
  final String? activeModal;
  final List<String> expandedSections;
  final ScrollPosition? scrollPosition;
}
```

## State Persistence Strategy

### HydratedBloc Implementation

#### Automatic Persistence
```dart
class ChatBloc extends HydratedBloc<ChatEvent, ChatState> {
  @override
  ChatState? fromJson(Map<String, dynamic> json) {
    try {
      return ChatState.fromJson(json);
    } catch (e) {
      // Handle migration or corruption gracefully
      return null; // Will use initial state
    }
  }

  @override
  Map<String, dynamic>? toJson(ChatState state) {
    try {
      return state.toJson();
    } catch (e) {
      // Log error but don't crash
      return null;
    }
  }
}
```

#### Storage Hierarchy
1. **Critical State**: Always persisted (settings, connection preferences)
2. **Important State**: Persisted with size limits (conversation history)
3. **Cache State**: Persisted temporarily (UI preferences)
4. **Ephemeral State**: Never persisted (loading states, animations)

### Data Synchronization

#### Local-First Strategy
- **Immediate local updates** for responsive UI
- **Background synchronization** with backend when connected
- **Conflict resolution** using last-write-wins with user notification
- **Offline queue** for actions taken while disconnected

#### Cross-Device Synchronization
- **Settings synchronization** across user's devices
- **Conversation continuity** when switching devices
- **Relationship data sharing** within trusted device network
- **Privacy-aware sync** respecting user privacy boundaries

## BLoC Lifecycle Management

### Registration Strategy
```dart
// Service registration in main.dart
void setupDependencies() {
  // Repositories (Singletons)
  GetIt.instance.registerLazySingleton<ChatRepository>(
    () => ChatRepository(GetIt.instance<ApiClient>()),
  );
  
  // BLoCs (Factories for fresh instances)
  GetIt.instance.registerFactory<ChatBloc>(
    () => ChatBloc(GetIt.instance<ChatRepository>()),
  );
  
  // Global BLoCs (Singletons for app-wide state)
  GetIt.instance.registerLazySingleton<ConnectionBloc>(
    () => ConnectionBloc(GetIt.instance<ConnectionRepository>()),
  );
}
```

### Widget Integration
```dart
// BlocProvider for feature-specific BLoCs
class ChatScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => GetIt.instance<ChatBloc>(),
      child: ChatView(),
    );
  }
}

// BlocConsumer for state listening and building
class ChatView extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return BlocConsumer<ChatBloc, ChatState>(
      listener: (context, state) {
        // Handle side effects (navigation, snackbars, etc.)
        if (state.hasError) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(state.errorMessage)),
          );
        }
      },
      builder: (context, state) {
        // Build UI based on state
        return ChatInterface(
          messages: state.messages,
          isLoading: state.isLoading,
          onMessageSent: (message) {
            context.read<ChatBloc>().add(MessageSent(content: message));
          },
        );
      },
    );
  }
}
```

## Error Handling

### State Error Management
```dart
// Base state with error handling
abstract class BaseState {
  final bool isLoading;
  final String? errorMessage;
  final Exception? exception;
  
  bool get hasError => errorMessage != null;
  bool get isIdle => !isLoading && !hasError;
}

// Error recovery events
abstract class BaseEvent {
  ErrorCleared()
  RetryRequested()
  StateReset()
}
```

### Error Recovery Patterns
- **Automatic retry** for transient errors
- **User-initiated retry** for persistent errors
- **Graceful degradation** when features are unavailable
- **Error boundary isolation** preventing cascade failures

## Testing Strategy

### BLoC Testing
```dart
// Unit testing BLoCs
group('ChatBloc', () {
  late ChatBloc chatBloc;
  late MockChatRepository mockRepository;

  setUp(() {
    mockRepository = MockChatRepository();
    chatBloc = ChatBloc(mockRepository);
  });

  blocTest<ChatBloc, ChatState>(
    'emits message sent state when MessageSent event is added',
    build: () => chatBloc,
    act: (bloc) => bloc.add(MessageSent(content: 'Hello')),
    expect: () => [
      ChatState.loading(),
      ChatState.messageSent(message: Message(content: 'Hello')),
    ],
  );
});
```

### Integration Testing
- **State persistence testing** verifying HydratedBloc functionality
- **Cross-BLoC communication** testing event propagation
- **Error scenario testing** ensuring graceful error handling
- **Performance testing** measuring state update efficiency

## Performance Optimization

### State Efficiency
- **Immutable state objects** using built_value or freezed
- **Selective rebuilds** using BlocBuilder with buildWhen
- **State normalization** avoiding nested object updates
- **Memory management** proper BLoC disposal

### Persistence Optimization
- **Selective persistence** only persisting necessary state
- **Compression** for large state objects
- **Migration strategies** for state schema changes
- **Background persistence** avoiding UI blocking

This state management specification ensures robust, performant, and maintainable state handling throughout the AICO frontend while supporting offline-first operation and cross-device synchronization.
