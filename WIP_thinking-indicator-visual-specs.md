# Thinking Indicator Visual Specifications & Mockups

**Version:** 1.0  
**Date:** October 21, 2025  
**Companion Document:** progressive-disclosure-thinking-indicator-2025.md

---

## Visual Mockups

### Layer 1: Ambient Presence (Collapsed State)

#### State 1: Idle (No Thoughts)
```
┌─────────────────────────────────────┐
│                                     │
│   [Conversation Area]               │
│                                     │
│                                     │
│                                     │
│                                     │
│                                     │
│                                     │
│                                     │
│                                     │
└─────────────────────────────────────┘
```
**Behavior:** No indicator visible. Drawer edge is clean.

---

#### State 2: Static (Thoughts Exist, Not Streaming)
```
┌─────────────────────────────────────┐
│                                 ╭─╮ │
│          Thought count badge →  │3│ │
│                                 ╰─╯ │
│   Vertical bar (subtle glow) →  │█│ │
│                                 │█│ │
│                                 │█│ │
│                                 │█│ │
│                                 │█│ │
│                                 │█│ │
│                                 │█│ │
│                                 │█│ │
└─────────────────────────────────────┘
```
**Visual Details:**
- Badge: 20px circle, glassmorphic, purple text
- Bar: 8px wide, purple gradient (0.3 opacity)
- Glow: 12px blur, 2px spread, purple (0.2 opacity)
- Badge opacity: 50% after 3 seconds

---

#### State 3: Active Streaming
```
┌─────────────────────────────────────┐
│                                 ╭─╮ │
│      Thought count (pulsing) →  │3│ │
│                                 ╰─╯ │
│     Vertical bar (breathing) →  │█│ │
│                                 │█│ │
│    Streaming icon (rotating) →  │✨││
│                                 │█│ │
│          Prominent glow →       │█│ │
│                                 │█│ │
│                                 │█│ │
│                                 │█│ │
└─────────────────────────────────────┘
```
**Visual Details:**
- Badge: Pulses on new thought (scale 1.0 → 1.2 → 1.0)
- Bar: Breathing animation (0.6 → 1.0 opacity, 3s cycle)
- Icon: 16px sparkles, rotates 360° over 3s
- Glow: Multi-layer (20px + 40px blur, 0.4-0.8 opacity)
- Shimmer: White overlay (0.15 opacity) moving vertically

---

### Layer 2: Contextual Preview (Hover State)

#### Preview Card - Active Streaming
```
┌─────────────────────────────────────────────────────┐
│                         ╭─╮                         │
│                         │3│                         │
│                         ╰─╯                         │
│  ┌──────────────────────┐│█│                        │
│  │ Inner Monologue [✨]│ │█│                        │
│  ├──────────────────────┤│✨│                       │
│  │ Just now             │ │█│                        │
│  │ Analyzing user's...  │ │█│                        │
│  │                      │ │█│                        │
│  │ 2m ago               │ │█│                        │
│  │ Retrieved memory...  │ │█│                        │
│  │                      │ │█│                        │
│  │ ⋮ 1 more thought     │ │█│                        │
│  │                      │ │█│                        │
│  │ [Expand for full →]  │ │█│                        │
│  └──────────────────────┘│█│                        │
└─────────────────────────────────────────────────────┘
```
**Note:** Preview card slides in from RIGHT, overlaying conversation area
**Visual Details:**
- Card: 280px × max 400px, glassmorphic
- Backdrop blur: 30px (heavy)
- Background: white 4% (dark) / 60% (light)
- Border: 1.5px, white 20% opacity
- Shadow: 40px blur, 8px offset, -10px spread
- Padding: 16px all sides
- Border radius: 20px (medium)

**Content Styling:**
- Header: 11px, medium weight, 60% opacity
- Live badge: Purple accent, 9px, 600 weight
- Timestamps: 10px, regular, 35% opacity
- Content: 12px, regular, 60% opacity, truncated at 60 chars
- Action hint: 11px, medium, purple accent

---

#### Preview Card - Static (No Streaming)
```
┌─────────────────────────────────────────────────────┐
│                         ╭─╮                         │
│                         │3│                         │
│                         ╰─╯                         │
│  ┌──────────────────────┐│█│                        │
│  │ Inner Monologue      │ │█│                        │
│  ├──────────────────────┤│█│                        │
│  │ 5m ago               │ │█│                        │
│  │ Completed reasoning..│ │█│                        │
│  │                      │ │█│                        │
│  │ 8m ago               │ │█│                        │
│  │ Retrieved context... │ │█│                        │
│  │                      │ │█│                        │
│  │ ⋮ 1 more thought     │ │█│                        │
│  │                      │ │█│                        │
│  │ [Expand for full →]  │ │█│                        │
│  └──────────────────────┘│█│                        │
└─────────────────────────────────────────────────────┘
```
**Differences from Streaming:**
- No "Live" badge in header
- No pulsing animations
- Timestamps show relative time (5m ago, 8m ago)
- Content is static (no live updates)

---

### Layer 3: Full Disclosure (Expanded Drawer)

```
┌─────────────────────────────────────────────────────────┐
│                                     │ Inner Monologue   │
│   [Conversation Area]               ├───────────────────┤
│                                     │ Just now   [✨Live]│
│                                     │ Analyzing user's  │
│                                     │ question about... │
│                                     │                   │
│                                     │ 2m ago            │
│                                     │ Retrieved memory: │
│                                     │ User mentioned... │
│                                     │                   │
│                                     │ 5m ago            │
│                                     │ Completed reason..│
│                                     │                   │
│                                     │ [Scroll for more] │
└─────────────────────────────────────────────────────────┘
```
**Visual Details:**
- Drawer width: 320px (expanded from 80px)
- Transition: 300ms ease-out-cubic
- Content: Full `ThinkingDisplay` widget (existing)
- Scrollable timeline with all thoughts
- Each thought card: 28px border radius, glassmorphic

---

## Animation Specifications

### 1. Breathing Pulse (Streaming State)

**Visual Effect:** Vertical bar opacity pulses rhythmically

```dart
AnimationController(
  duration: Duration(milliseconds: 3000),
  vsync: this,
)..repeat(reverse: true);

Animation<double> _pulseAnimation = Tween<double>(
  begin: 0.6,
  end: 1.0,
).animate(CurvedAnimation(
  parent: _pulseController,
  curve: Curves.easeInOut,
));
```

**Keyframes:**
```
0ms:    opacity 0.6  (dim)
1500ms: opacity 1.0  (bright)
3000ms: opacity 0.6  (dim)
```

**Glow Intensity:**
```
0ms:    blur 20px, spread 4px, opacity 0.4
1500ms: blur 36px, spread 4px, opacity 0.8
3000ms: blur 20px, spread 4px, opacity 0.4
```

---

### 2. Thought Count Badge Pulse (New Thought)

**Visual Effect:** Badge scales up and bounces back

```dart
AnimationController(
  duration: Duration(milliseconds: 600),
  vsync: this,
);

Animation<double> _badgePulse = Tween<double>(
  begin: 1.0,
  end: 1.2,
).animate(CurvedAnimation(
  parent: _badgeController,
  curve: Curves.elasticOut,
));
```

**Keyframes:**
```
0ms:   scale 1.0   (normal)
200ms: scale 1.2   (expanded)
400ms: scale 0.95  (bounce back)
600ms: scale 1.0   (settled)
```

---

### 3. Streaming Icon Rotation

**Visual Effect:** Sparkles icon rotates continuously

```dart
AnimationController(
  duration: Duration(milliseconds: 3000),
  vsync: this,
)..repeat();

Animation<double> _rotationAnimation = Tween<double>(
  begin: 0.0,
  end: 2 * pi,
).animate(_rotationController);
```

**Transform:**
```dart
Transform.rotate(
  angle: _rotationAnimation.value,
  child: Icon(Icons.auto_awesome_rounded),
)
```

---

### 4. Preview Card Slide-In

**Visual Effect:** Card slides from right with fade-in

```dart
AnimationController(
  duration: Duration(milliseconds: 200),
  vsync: this,
);

Animation<Offset> _slideAnimation = Tween<Offset>(
  begin: Offset(20, 0),  // Slide from RIGHT
  end: Offset.zero,
).animate(CurvedAnimation(
  parent: _slideController,
  curve: Curves.easeOut,
));

Animation<double> _fadeAnimation = Tween<double>(
  begin: 0.0,
  end: 1.0,
).animate(_slideController);
```

**Keyframes:**
```
0ms:   x: +20px, opacity: 0.0  (from right)
100ms: x: +10px, opacity: 0.5
200ms: x: 0px,   opacity: 1.0
```

---

### 5. Drawer Expansion

**Visual Effect:** Drawer width expands smoothly

```dart
AnimationController(
  duration: Duration(milliseconds: 300),
  vsync: this,
);

Animation<double> _widthAnimation = Tween<double>(
  begin: 80.0,
  end: 320.0,
).animate(CurvedAnimation(
  parent: _expansionController,
  curve: Curves.easeOutCubic,
));
```

**Keyframes:**
```
0ms:   width: 80px   (collapsed)
150ms: width: 240px  (mid-expansion)
300ms: width: 320px  (fully expanded)
```

---

## Color Specifications

### Dark Mode Palette

```dart
// Primary accent
final purpleAccent = Color(0xFFB9A7E6);

// Glassmorphic surfaces
final glassBackground = Colors.white.withValues(alpha: 0.04);
final glassBorder = Colors.white.withValues(alpha: 0.20);
final glassBackgroundHover = Colors.white.withValues(alpha: 0.06);

// Text hierarchy
final textPrimary = Colors.white.withValues(alpha: 0.90);
final textSecondary = Colors.white.withValues(alpha: 0.60);
final textTertiary = Colors.white.withValues(alpha: 0.35);

// Shadows and glows
final shadowColor = Colors.black.withValues(alpha: 0.40);
final glowColor = purpleAccent.withValues(alpha: 0.40);

// Streaming states
final streamingGlow = purpleAccent.withValues(alpha: 0.60);
final staticGlow = purpleAccent.withValues(alpha: 0.30);
```

### Light Mode Palette

```dart
// Primary accent
final purpleAccent = Color(0xFFB8A1EA);

// Glassmorphic surfaces
final glassBackground = Colors.white.withValues(alpha: 0.60);
final glassBorder = Colors.white.withValues(alpha: 0.40);
final glassBackgroundHover = Colors.white.withValues(alpha: 0.70);

// Text hierarchy
final textPrimary = Colors.black.withValues(alpha: 0.90);
final textSecondary = Colors.black.withValues(alpha: 0.70);
final textTertiary = Colors.black.withValues(alpha: 0.45);

// Shadows and glows
final shadowColor = Colors.black.withValues(alpha: 0.08);
final glowColor = purpleAccent.withValues(alpha: 0.30);

// Streaming states
final streamingGlow = purpleAccent.withValues(alpha: 0.50);
final staticGlow = purpleAccent.withValues(alpha: 0.25);
```

---

## Dimension Specifications

### Layout Measurements

```dart
// Ambient bar (Layer 1)
const double barWidth = 8.0;
const double barGlowRadius = 20.0;
const double barGlowSpread = 4.0;

// Thought count badge
const double badgeSize = 20.0;
const double badgeFontSize = 10.0;
const double badgePadding = 4.0;

// Streaming icon
const double iconSize = 16.0;
const double iconTouchTarget = 24.0;

// Preview card (Layer 2)
const double previewWidth = 280.0;
const double previewMaxHeight = 400.0;
const double previewPadding = 16.0;
const double previewBorderRadius = 20.0;
const double previewBorderWidth = 1.5;
const double previewBlur = 30.0;

// Preview content
const double previewHeaderFontSize = 11.0;
const double previewTimestampFontSize = 10.0;
const double previewContentFontSize = 12.0;
const double previewActionFontSize = 11.0;
const double previewLineHeight = 1.5;
const int previewContentTruncateLength = 60;

// Expanded drawer (Layer 3)
const double drawerCollapsedWidth = 80.0;
const double drawerExpandedWidth = 320.0;
const double drawerPadding = 16.0;

// Spacing (8px grid)
const double spacing1 = 8.0;   // 1×8
const double spacing2 = 16.0;  // 2×8
const double spacing3 = 24.0;  // 3×8
const double spacing4 = 32.0;  // 4×8
```

### Shadow Specifications

```dart
// Ambient bar glow (streaming)
final streamingShadows = [
  BoxShadow(
    color: purpleAccent.withValues(alpha: 0.4 + pulseValue * 0.4),
    blurRadius: 20 + (pulseValue * 16),
    spreadRadius: 4,
    offset: Offset.zero,
  ),
  BoxShadow(
    color: purpleAccent.withValues(alpha: 0.2 + pulseValue * 0.3),
    blurRadius: 40 + (pulseValue * 24),
    spreadRadius: 8,
    offset: Offset.zero,
  ),
];

// Ambient bar glow (static)
final staticShadows = [
  BoxShadow(
    color: purpleAccent.withValues(alpha: 0.2),
    blurRadius: 12,
    spreadRadius: 2,
    offset: Offset.zero,
  ),
];

// Preview card floating depth
final previewShadows = [
  BoxShadow(
    color: Colors.black.withValues(alpha: 0.3),
    blurRadius: 40,
    offset: Offset(8, 0),
    spreadRadius: -10,
  ),
  BoxShadow(
    color: purpleAccent.withValues(alpha: 0.1),
    blurRadius: 60,
    offset: Offset.zero,
    spreadRadius: -5,
  ),
];
```

---

## Interaction Specifications

### Hover Behavior (Desktop)

**Trigger:** Mouse enters bar area  
**Delay:** 300ms (prevents accidental triggers)  
**Action:** Show preview card

```dart
MouseRegion(
  onEnter: (_) => _startHoverTimer(),
  onExit: (_) => _cancelHoverTimer(),
  child: AmbientThinkingIndicator(...),
)

void _startHoverTimer() {
  _hoverTimer = Timer(Duration(milliseconds: 300), () {
    setState(() => _showPreview = true);
  });
}
```

**Preview Dismissal:**
- Mouse leaves bar + preview area
- Click outside preview
- Drawer expands (preview auto-hides)

---

### Long-Press Behavior (Mobile)

**Trigger:** Touch down on bar area  
**Duration:** 500ms hold  
**Feedback:** Haptic feedback on trigger

```dart
GestureDetector(
  onLongPressStart: (_) => _startLongPress(),
  onLongPressEnd: (_) => _showPreview(),
  child: AmbientThinkingIndicator(...),
)

void _showPreview() {
  HapticFeedback.mediumImpact();
  setState(() => _showPreview = true);
}
```

**Preview Dismissal:**
- Tap outside preview
- Swipe down gesture
- Drawer expands

---

### Tap Behavior (All Devices)

**Trigger:** Single tap on bar, badge, or icon  
**Action:** Expand drawer to full view

```dart
GestureDetector(
  onTap: () => _expandDrawer(),
  child: AmbientThinkingIndicator(...),
)

void _expandDrawer() {
  setState(() {
    _isRightDrawerExpanded = true;
    _showPreview = false; // Hide preview when expanding
  });
  _expansionController.forward();
}
```

---

## Accessibility Specifications

### Semantic Labels

```dart
Semantics(
  label: 'Thinking indicator',
  hint: _getAccessibilityHint(),
  button: true,
  onTap: _expandDrawer,
  child: AmbientThinkingIndicator(...),
)

String _getAccessibilityHint() {
  if (isStreaming) {
    return 'AICO is actively thinking. Press to view reasoning process.';
  } else if (thoughtCount > 0) {
    return 'AICO has $thoughtCount thoughts. Press to view history.';
  } else {
    return 'No thoughts available.';
  }
}
```

### Keyboard Navigation

```dart
Focus(
  onKey: (node, event) {
    if (event is RawKeyDownEvent) {
      if (event.logicalKey == LogicalKeyboardKey.enter ||
          event.logicalKey == LogicalKeyboardKey.space) {
        _expandDrawer();
        return KeyEventResult.handled;
      }
    }
    return KeyEventResult.ignored;
  },
  child: AmbientThinkingIndicator(...),
)
```

### Reduced Motion Support

```dart
final reducedMotion = MediaQuery.of(context).disableAnimations;

// Disable breathing animation
if (reducedMotion) {
  return Container(
    decoration: BoxDecoration(
      color: purpleAccent.withValues(alpha: 0.6), // Static opacity
      boxShadow: staticShadows, // No animated glow
    ),
  );
}

// Use instant transitions
final transitionDuration = reducedMotion 
    ? Duration.zero 
    : Duration(milliseconds: 300);
```

---

## Performance Optimization

### Animation Isolation

```dart
// Wrap animated elements in RepaintBoundary
RepaintBoundary(
  child: AnimatedBuilder(
    animation: _pulseAnimation,
    builder: (context, child) {
      return Container(
        decoration: BoxDecoration(
          boxShadow: _buildAnimatedShadows(),
        ),
      );
    },
  ),
)
```

### Lazy Loading

```dart
// Only build preview card when needed
Widget _buildPreviewIfNeeded() {
  if (!_showPreview) {
    return SizedBox.shrink();
  }
  
  return ThinkingPreviewCard(
    recentThoughts: _getRecentThoughts(),
    streamingThought: widget.streamingThought,
    onExpand: _expandDrawer,
  );
}
```

### Frame Rate Monitoring

```dart
// Debug mode only
if (kDebugMode) {
  SchedulerBinding.instance.addTimingsCallback((timings) {
    for (final timing in timings) {
      final fps = 1000 / timing.totalSpan.inMilliseconds;
      if (fps < 55) {
        debugPrint('⚠️ Low FPS detected: $fps');
      }
    }
  });
}
```

---

## Testing Checklist

### Visual Regression Tests

- [ ] Ambient bar renders correctly in all states (idle, static, streaming)
- [ ] Thought count badge displays correct number
- [ ] Streaming icon rotates smoothly
- [ ] Preview card positions correctly on all screen sizes
- [ ] Drawer expansion animation is smooth
- [ ] Colors match specifications in both themes

### Animation Performance Tests

- [ ] Breathing pulse maintains 60fps
- [ ] Badge pulse animation completes in 600ms
- [ ] Icon rotation is smooth (no jank)
- [ ] Preview slide-in completes in 200ms
- [ ] Drawer expansion completes in 300ms
- [ ] No dropped frames during simultaneous animations

### Interaction Tests

- [ ] Hover triggers preview after 300ms delay
- [ ] Hover cancellation prevents preview
- [ ] Long-press triggers preview on mobile
- [ ] Tap expands drawer
- [ ] Preview dismisses on outside click
- [ ] Keyboard navigation works (Tab, Enter, Escape)

### Accessibility Tests

- [ ] Screen reader announces correct labels
- [ ] Keyboard focus visible
- [ ] Reduced motion disables animations
- [ ] Touch targets meet 44×44px minimum
- [ ] Color contrast meets WCAG AA
- [ ] Semantic structure is logical

---

## Implementation Priority

### Must-Have (MVP)
1. ✅ Ambient bar with breathing animation
2. ✅ Thought count badge
3. ✅ Streaming icon with rotation
4. ✅ Basic preview card on hover
5. ✅ Drawer expansion on click

### Should-Have (V1.1)
6. ⏳ Preview card truncation and formatting
7. ⏳ Smooth animation transitions
8. ⏳ Mobile long-press support
9. ⏳ Reduced motion support
10. ⏳ Keyboard navigation

### Nice-to-Have (V1.2)
11. 💡 Haptic feedback on mobile
12. 💡 First-time user tooltip
13. 💡 Preview card smart positioning
14. 💡 Animation performance monitoring
15. 💡 Advanced accessibility features

---

## Conclusion

This visual specification provides pixel-perfect guidance for implementing the three-layer progressive disclosure system for AICO's thinking indicator. All measurements, colors, animations, and interactions are precisely defined to ensure award-winning visual fidelity while maintaining AICO's core design principles of immersion, emotional presence, and user-centered design.
