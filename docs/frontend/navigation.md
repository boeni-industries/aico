---
title: Navigation Architecture
---

# Navigation Architecture

## Overview

AICO's navigation architecture implements a flat, intuitive structure that prioritizes immediate access to core functionality while supporting deep linking and cross-platform consistency. The design follows the **progressive disclosure** paradigm, revealing complexity only when needed.

## Navigation Principles

### 🎯 Flat Information Architecture
- Maximum 4-5 root-level sections to prevent cognitive overload
- No deep nesting - all major functions accessible within 2 taps/clicks
- Clear visual hierarchy with consistent navigation patterns

### 🔗 Universal Deep Linking
- Every screen accessible via direct URL for bookmarking and sharing
- Consistent URL structure across web, desktop, and mobile platforms
- State preservation through navigation parameters

### 📱 Platform-Adaptive Patterns
- **Mobile**: Bottom tab navigation for thumb-friendly access
- **Desktop**: Vertical sidebar with collapsible sections
- **Web**: Browser-friendly URLs with back/forward support

## Information Architecture

### Primary Navigation Structure

```
Home (Avatar Central)
├── Chat
│   ├── Active Conversation
│   ├── Conversation History
│   └── Voice/Text Input
├── Relationships
│   ├── Family Members
│   ├── Interaction History
│   └── Privacy Settings
├── Memory
│   ├── Personal Timeline
│   ├── Shared Experiences
│   └── Memory Search
├── Settings
│   ├── Preferences
│   ├── Privacy Controls
│   ├── System Configuration
│   └── About/Updates
└── Admin (Developer/Advanced)
    ├── System Status
    ├── Logs & Diagnostics
    ├── Plugin Management
    └── Developer Tools
```

### URL Structure

**Web/Desktop URL Patterns:**
```
/                           # Home (Avatar Central)
/chat                       # Active conversation
/chat/history              # Conversation history
/chat/[conversation-id]    # Specific conversation
/relationships             # Relationship overview
/relationships/[person-id] # Individual relationship
/memory                    # Memory timeline
/memory/search            # Memory search
/settings                 # User preferences
/settings/privacy         # Privacy controls
/admin                    # Admin dashboard
/admin/logs              # System logs
```

**Mobile Deep Link Patterns:**
```
aico://home
aico://chat
aico://chat/[conversation-id]
aico://relationships/[person-id]
aico://memory/search?q=[query]
aico://settings/privacy
```

## Navigation Components

### Primary Navigation

#### Mobile Bottom Tab Bar
- **Home**: Avatar and quick actions
- **Chat**: Active conversation access
- **People**: Relationship management
- **Memory**: Personal timeline
- **More**: Settings and additional features

#### Desktop Sidebar
- **Collapsible sections** with clear visual grouping
- **Quick access icons** for frequently used functions
- **Contextual sub-navigation** that appears based on current section
- **Search integration** within navigation for large data sets

### Secondary Navigation

#### Contextual Navigation
- **Breadcrumbs**: Clear path indication for nested content
- **Back/Forward**: Consistent browser-like navigation
- **Tab Groups**: Related content organization within sections

#### Modal Navigation
- **Settings overlays**: Non-disruptive configuration access
- **Quick actions**: Floating action buttons for primary tasks
- **Search interfaces**: Full-screen search with contextual results

## State Management

### Navigation State Persistence

#### Route State
- **Current location**: Preserved across app restarts
- **Navigation history**: Back/forward stack maintenance
- **Tab state**: Active tab preservation in multi-tab interfaces

#### Deep Link Handling
- **Parameter parsing**: URL/deep link parameter extraction
- **State reconstruction**: Rebuilding app state from navigation parameters
- **Fallback routes**: Graceful handling of invalid or expired links

### Cross-Platform Synchronization

#### State Sharing
- **Navigation preferences**: Synchronized across devices
- **Bookmarks/favorites**: Shared navigation shortcuts
- **Recent locations**: Cross-device navigation history

## Implementation Patterns

### Declarative Routing (go_router)

#### Route Configuration
```dart
// Route tree structure
GoRouter(
  routes: [
    // Shell route for persistent navigation
    ShellRoute(
      builder: (context, state, child) => MainLayout(child: child),
      routes: [
        GoRoute(
          path: '/',
          name: 'home',
          builder: (context, state) => HomeScreen(),
        ),
        GoRoute(
          path: '/chat',
          name: 'chat',
          builder: (context, state) => ChatScreen(),
          routes: [
            GoRoute(
              path: '/history',
              name: 'chat-history',
              builder: (context, state) => ChatHistoryScreen(),
            ),
            GoRoute(
              path: '/:conversationId',
              name: 'conversation',
              builder: (context, state) => ConversationScreen(
                conversationId: state.pathParameters['conversationId']!,
              ),
            ),
          ],
        ),
      ],
    ),
  ],
)
```

#### Navigation Guards
- **Authentication checks**: Redirect to login if required
- **Permission validation**: Access control for admin sections
- **State validation**: Ensure required data is available

### Navigation State Management

#### Navigation BLoC
- **Route changes**: Track and manage navigation state
- **Deep link handling**: Process incoming deep links
- **State persistence**: Maintain navigation state across sessions

#### Route Parameters
- **Type-safe parameters**: Strongly typed route parameters
- **Validation**: Parameter validation and sanitization
- **Default values**: Fallback values for optional parameters

## User Experience Patterns

### Progressive Disclosure

#### Information Layering
- **Overview first**: High-level information before details
- **Drill-down navigation**: Progressive detail revelation
- **Context preservation**: Maintain user's place in information hierarchy

#### Adaptive Complexity
- **Beginner mode**: Simplified navigation for new users
- **Expert mode**: Advanced navigation options for power users
- **Contextual help**: Navigation assistance based on user behavior

### Accessibility

#### Keyboard Navigation
- **Tab order**: Logical keyboard navigation sequence
- **Focus management**: Clear focus indicators and management
- **Shortcuts**: Keyboard shortcuts for common navigation actions

#### Screen Reader Support
- **Semantic navigation**: Proper heading structure and landmarks
- **Navigation announcements**: Clear communication of location changes
- **Skip links**: Quick navigation to main content areas

## Error Handling

### Navigation Errors

#### Invalid Routes
- **404 handling**: Graceful handling of non-existent routes
- **Redirect strategies**: Intelligent fallback routing
- **Error recovery**: User-friendly error messages with recovery options

#### State Corruption
- **State validation**: Check for corrupted navigation state
- **Reset mechanisms**: Options to reset navigation to known good state
- **Diagnostic information**: Helpful error reporting for debugging

### Offline Navigation

#### Cached Routes
- **Route caching**: Cache frequently accessed routes for offline use
- **Offline indicators**: Clear indication of offline-only content
- **Sync indicators**: Show when navigation state will sync

## Performance Considerations

### Route Optimization

#### Lazy Loading
- **Code splitting**: Load route components on demand
- **Preloading**: Intelligent preloading of likely next routes
- **Bundle optimization**: Minimize initial navigation bundle size

#### State Efficiency
- **Minimal state**: Keep navigation state lean and focused
- **Efficient updates**: Optimize navigation state change performance
- **Memory management**: Proper cleanup of navigation state

### Animation Performance

#### Smooth Transitions
- **Hardware acceleration**: Use GPU-accelerated animations
- **Reduced motion**: Respect user accessibility preferences
- **Performance monitoring**: Track navigation animation performance

This navigation architecture ensures users can efficiently access AICO's functionality while maintaining consistency across platforms and supporting both novice and expert usage patterns.
