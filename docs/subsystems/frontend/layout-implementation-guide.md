---
title: Layout System Implementation Guide
---

# Layout System Implementation Guide

## Overview

This guide shows how to integrate the modal-aware layout system into AICO's home screen for Phase 1 implementation (Initial State + Text Mode).

## Created Components

### 1. Layout Provider (`/lib/presentation/providers/layout_provider.dart`)
**Status:** ✅ Created, code generated

**Usage:**
```dart
// Watch layout state
final layoutState = ref.watch(layoutProvider);

// Switch modality
ref.read(layoutProvider.notifier).switchModality(ConversationModality.text);

// Toggle voice/text
ref.read(layoutProvider.notifier).toggleVoiceText();

// Update thinking state
ref.read(layoutProvider.notifier).setThinking(true);
```

### 2. Responsive Breakpoints (`/lib/core/responsive/breakpoints.dart`)
**Status:** ✅ Created

**Usage:**
```dart
// Check platform
if (context.isMobilePortrait) { /* vertical layout */ }
if (context.isDesktop) { /* desktop features */ }

// Get responsive values
final padding = context.horizontalPadding; // 16-40px
final maxWidth = context.messageMaxWidth; // 800px desktop, 95% mobile

// Explicit checks
if (Breakpoints.shouldUseVerticalLayout(context)) {
  // Stack avatar top, messages bottom
}
```

### 3. Modal-Aware Layout (`/lib/presentation/widgets/layouts/modal_aware_layout.dart`)
**Status:** ✅ Created

**Usage:**
```dart
ModalAwareLayout(
  avatar: AvatarWebViewContainer(webView: myWebView),
  messages: ConversationMessageList(),
  input: HomeInputArea(),
  sidebar: HomeLeftDrawer(), // Optional, desktop only
)
```

### 4. Animated Avatar Container (`/lib/presentation/widgets/avatar/animated_avatar_container.dart`)
**Status:** ✅ Created

**Usage:**
```dart
AnimatedAvatarContainer(
  child: InAppWebView(...), // Automatically handles sizing & transitions
)
```

## Integration Steps

### Phase 1: Initial State + Text Mode

#### Step 1: Update HomeScreen Scaffold Structure

**Current Structure:**
```dart
Scaffold(
  body: Container(
    decoration: BoxDecoration(gradient: ...),
    child: Stack([
      // Mood glow
      // Row with left drawer, main content, right drawer
    ]),
  ),
)
```

**Target Structure:**
```dart
Scaffold(
  body: Stack([
    // Layer 0: Background gradient
    _EnvironmentalGradient(),
    
    // Layer 1-5: Main content
    Row([
      if (context.isDesktop) HomeLeftDrawer(),
      
      Expanded(
        child: ModalAwareLayout(
          avatar: _buildAvatar(),
          messages: _buildMessages(),
          input: _buildInput(),
        ),
      ),
      
      if (context.isDesktop && _isRightDrawerOpen) HomeRightDrawer(),
    ]),
  ]),
)
```

#### Step 2: Extract Avatar Building

**Create method:**
```dart
Widget _buildAvatar() {
  return AnimatedAvatarContainer(
    child: AvatarWebViewContainer(
      webView: InAppWebView(
        initialUrlRequest: URLRequest(
          url: Uri.parse('http://localhost:8080/viewer.html'),
        ),
        onWebViewCreated: (controller) {
          // Store controller
        },
        onLoadStop: (controller, url) async {
          // Sync layout state to Three.js
          final layoutState = ref.read(layoutProvider);
          await controller.evaluateJavascript(
            source: 'updateLayout("${layoutState.modality.name}")',
          );
        },
      ),
    ),
  );
}
```

#### Step 3: Extract Messages Building

**Create method:**
```dart
Widget _buildMessages() {
  final messages = ref.watch(conversationProvider).messages;
  
  if (messages.isEmpty) {
    return _buildWelcomeMessage();
  }
  
  return ListView.builder(
    controller: _conversationController,
    reverse: true,
    padding: EdgeInsets.symmetric(
      horizontal: context.horizontalPadding,
      vertical: 16,
    ),
    itemCount: messages.length,
    itemBuilder: (context, index) {
      return InteractiveMessageBubble(
        message: messages[index],
      );
    },
  );
}
```

#### Step 4: Extract Input Building

**Create method:**
```dart
Widget _buildInput() {
  return Container(
    constraints: BoxConstraints(
      maxWidth: context.inputMaxWidth,
    ),
    child: HomeInputArea(
      controller: _messageController,
      focusNode: _messageFocusNode,
      onSend: _handleSendMessage,
      onVoiceToggle: () {
        ref.read(layoutProvider.notifier).toggleVoiceText();
      },
    ),
  );
}
```

#### Step 5: Update Input Area Widget

**Add voice/text toggle to HomeInputArea:**
```dart
// In home_input_area.dart
class HomeInputArea extends ConsumerWidget {
  final VoidCallback? onVoiceToggle;
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final layoutState = ref.watch(layoutProvider);
    final isVoiceMode = layoutState.modality == ConversationModality.voice;
    
    return Row([
      // Text input field
      Expanded(child: TextField(...)),
      
      // Voice/Text toggle button
      IconButton(
        icon: Icon(isVoiceMode ? Icons.keyboard : Icons.mic),
        onPressed: onVoiceToggle,
      ),
      
      // Send button
      IconButton(
        icon: Icon(Icons.send),
        onPressed: onSend,
      ),
    ]);
  }
}
```

#### Step 6: Connect to Conversation State

**Update message sending:**
```dart
Future<void> _handleSendMessage(String text) async {
  // Switch to text mode when sending message
  ref.read(layoutProvider.notifier).switchModality(ConversationModality.text);
  
  // Existing send logic
  await ref.read(conversationProvider.notifier).sendMessage(text);
}
```

**Update thinking state:**
```dart
// In conversation_provider.dart
Future<void> sendMessage(String text) async {
  // Set thinking state
  ref.read(layoutProvider.notifier).setThinking(true);
  
  try {
    // Send message
    await _apiClient.sendMessage(text);
  } finally {
    // Clear thinking state
    ref.read(layoutProvider.notifier).setThinking(false);
  }
}
```

## Testing Checklist

### Desktop (≥1024px)
- [ ] Initial state: Avatar centered, 70-80% height
- [ ] First message: Avatar slides left to 30%, messages appear right 70%
- [ ] Layout stable during conversation (no per-message shifting)
- [ ] Smooth 800ms transitions
- [ ] Thinking state: Avatar scales to 0.95, glow pulses
- [ ] Left drawer: Collapsible, doesn't affect avatar/message layout
- [ ] Right drawer: Collapsible, doesn't affect avatar/message layout

### Tablet (768-1023px)
- [ ] Same as desktop but no persistent sidebar
- [ ] Collapsible drawer from edge
- [ ] Avatar and messages use same horizontal layout

### Mobile Portrait (<768px)
- [ ] Initial state: Avatar centered, 70% height
- [ ] First message: Avatar moves to top 40%, messages bottom 60%
- [ ] Vertical stacking (not side-by-side)
- [ ] Full width components
- [ ] Bottom navigation instead of sidebar

### Mobile Landscape
- [ ] Uses desktop horizontal layout (avatar left, messages right)
- [ ] Side-by-side works with landscape width

## Performance Considerations

### Optimization Checklist
- [ ] Use `const` constructors where possible
- [ ] `RepaintBoundary` around avatar WebView
- [ ] Lazy-load off-screen messages
- [ ] Cache layout calculations in provider
- [ ] Minimize rebuilds with `Consumer` widgets
- [ ] Hardware-accelerated transforms only (no layout-triggering animations)

### Animation Performance
- [ ] All transitions use `AnimatedContainer`/`AnimatedAlign` (no manual controllers)
- [ ] 800ms duration with cubic-bezier curve
- [ ] Limit simultaneous animations to 3-4
- [ ] No layout shifts during animation

## Future Phases

### Phase 2: Voice Mode
- [ ] Implement voice indicator animations (pulsing ring)
- [ ] Add floating captions for accessibility
- [ ] Implement "slide up chat" interaction
- [ ] Add voice recording UI

### Phase 3: Hybrid Mode
- [ ] Implement 40/60 balanced layout
- [ ] Show both voice indicator and message history
- [ ] Add seamless switching between all three modes

## Troubleshooting

### Layout not updating
**Check:** Is `layoutProvider` being watched?
```dart
final layoutState = ref.watch(layoutProvider); // ✅ Correct
final layoutState = ref.read(layoutProvider);  // ❌ Won't rebuild
```

### Transitions not smooth
**Check:** Are you using `AnimatedContainer`?
```dart
AnimatedContainer(duration: 800ms, ...) // ✅ Smooth
Container(...)                          // ❌ Instant jump
```

### Avatar not resizing
**Check:** Is `AnimatedAvatarContainer` wrapping the WebView?
```dart
AnimatedAvatarContainer(child: webView) // ✅ Animated
webView                                  // ❌ Static
```

### Mobile layout wrong
**Check:** Is `shouldUseVerticalLayout` being used?
```dart
context.shouldUseVerticalLayout // ✅ Responsive
context.isMobile                // ❌ Doesn't check orientation
```

## Next Steps

1. **Backup current home_screen.dart**
2. **Implement Step 1-4** (scaffold restructuring)
3. **Test on desktop** (easiest to debug)
4. **Test on mobile** (verify vertical stacking)
5. **Add voice toggle** (Step 5)
6. **Connect conversation state** (Step 6)
7. **Polish transitions** (adjust timing if needed)

## Code Generation

After creating/modifying providers, run:
```bash
cd frontend
dart run build_runner build --delete-conflicting-outputs
```

This generates the `.g.dart` files for Riverpod providers.
