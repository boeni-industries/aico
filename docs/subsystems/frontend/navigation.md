---
title: Navigation Architecture
---

# Navigation Architecture

## Overview

AICO's navigation architecture implements an **adaptive hub-and-spoke** design that prioritizes emotional presence and zero-barrier interaction. The system uses progressive disclosure to reveal complexity gradually while maintaining avatar-centric design and cross-platform consistency.

## Navigation Principles

### 🎯 Avatar-Centric Design
- Central avatar serves as primary visual anchor and interaction point
- Navigation supports rather than competes with avatar presence
- Emotional state and system transparency integrated into navigation

### 🌊 Progressive Disclosure
- 4 core sections prevent cognitive overload
- Advanced features accessible through "More" section
- Admin functions behind additional authentication layer
- Context-sensitive navigation appears when needed

### 🔗 Universal Deep Linking
- Every screen accessible via direct URL for bookmarking and sharing
- Consistent URL structure across web, desktop, and mobile platforms
- State preservation through navigation parameters

### 📱 Platform-Adaptive Patterns
- **Mobile**: Bottom tab navigation with floating voice action
- **Desktop**: Collapsible sidebar with persistent avatar area
- **Web**: Hybrid approach supporting both interaction patterns

## Core Navigation Architecture

### Primary Navigation Structure (Hub-and-Spoke)

```
🏠 Home (Avatar Central Hub)
├── Avatar Display (96px with mood ring)
├── Persistent Voice/Text Input
├── Proactive Suggestions (dismissible cards)
├── System Status (subtle indicators)
└── Quick Actions (contextual)

💬 Conversation (Active Conversations)
├── Current Conversation
├── Conversation History (swipe/slide access)
├── Voice/Text Input Integration
└── Conversation Context

👥 People (Relationships)
├── Family Member Overview
├── Individual Relationship Details
├── Interaction History
├── Privacy Settings per Person
└── Recognition Management

⚙️ More (Organized by Usage Frequency)
├── Memory & Timeline
│   ├── Personal Timeline
│   ├── Shared Experiences
│   └── Memory Search
├── Settings
│   ├── Appearance & Theme
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
/                           # Home (Avatar Central Hub)
/conversation                       # Active conversation
/conversation/history              # Conversation history  
/conversation/[conversation-id]    # Specific conversation
/people                    # Relationships overview
/people/[person-id]        # Individual relationship
/more                      # More section hub
/more/memory               # Memory timeline
/more/memory/search        # Memory search
/more/settings             # User preferences
/more/settings/privacy     # Privacy controls
/more/admin                # Admin dashboard
/more/admin/logs           # System logs
```

**Mobile Deep Link Patterns:**
```
aico://home
aico://conversation
aico://conversation/[conversation-id]
aico://people/[person-id]
aico://more/memory/search?q=[query]
aico://more/settings/privacy
aico://more/admin
```

## Navigation Components

### Primary Navigation Sections

### 1. Home (Avatar Central Hub)
- **Route**: `/`
- **Purpose**: Avatar-centric emotional presence and system status
- **Features**: Mood ring, proactive suggestions, quick actions

### 2. Conversation (Active Conversations)
- **Route**: `/conversation`
- **Purpose**: Active conversation interface with AICO
- **Sub-routes**:
  - `/conversation/history` - Conversation history
  - `/conversation/:id` - Specific conversation threads
- **Floating Voice Button**: Overlays center for immediate voice input

#### Desktop Sidebar
- **Avatar Area**: Persistent 96px avatar with mood indicators
- **Collapsible sections** with soft purple accent for active states
- **Contextual sub-navigation** slides in based on current section
- **Search integration** for memory and conversation history

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
          path: '/conversation',
          name: 'conversation',
          builder: (context, state) => ConversationScreen(),
          routes: [
            GoRoute(
              path: '/history',
              name: 'conversation-history',
              builder: (context, state) => ConversationHistoryScreen(),
            ),
            GoRoute(
              path: '/:conversationId',
              name: 'conversation-detail',
              builder: (context, state) => ConversationDetailScreen(
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

#### Navigation with Riverpod
- **Route changes**: Track and manage navigation state through providers
- **Deep link handling**: Process incoming deep links with go_router integration
- **State persistence**: Maintain navigation preferences through shared preferences

```dart
// Navigation state provider
final navigationStateProvider = StateNotifierProvider<NavigationNotifier, NavigationState>((ref) {
  return NavigationNotifier();
});

// Current route provider
final currentRouteProvider = Provider<String>((ref) {
  return GoRouter.of(context).location;
});
```

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
