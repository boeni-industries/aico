---
title: UI Layout System
---

# UI Layout System

## Overview

AICO's UI layout system defines how screens are composed, how the avatar integrates with other elements, and how spatial relationships create immersive, emotionally present experiences. This document bridges design principles and component implementation, providing concrete layout patterns for building AICO's interface.

## Core Layout Principles

### Avatar-First Composition
- **Avatar dominates visual hierarchy** - occupies 60-70% of vertical space
- **Other elements support avatar presence** - never compete for attention
- **Spatial relationships reinforce emotional connection** - elements flow from/to avatar

### Modal-Aware Spatial Hierarchy
- **Voice mode**: Avatar center stage (70-80% height), chat minimized
- **Text mode**: Avatar left (30%), chat prominent (70%)
- **Hybrid mode**: Avatar balanced (40%), chat visible (60%)
- **Thinking state**: Avatar slightly receded, increased glow (any mode)

### Floating Organic Layout
- **16-40px padding from edges** - nothing touches screen boundaries
- **16-24px spacing between elements** - breathing room throughout
- **Layered elevation** - depth through glassmorphic surfaces
- **Organic curves** - 36px XL, 28px L, 20px M, 12px S radii

## Screen Layouts

### Home Screen (Avatar Central Hub)

**Initial State (No Active Conversation):**
```
┌─────────────────────────────────────────────┐
│  [Sidebar]      [Avatar Area 70%]     [Side]│
│   72-240px         Centered            Panel │
│                                              │
│               ╭─────────────╮               │
│               │   Avatar    │               │
│               │  Full Body  │               │
│               │  Breathing  │               │
│               ╰─────────────╯               │
│                                              │
│          [Quick Actions / Prompts]          │
│           Subtle, dismissible               │
│                                              │
│     [Input Field - Persistent Bottom]       │
│      Voice/Text toggle, 36px radius         │
└─────────────────────────────────────────────┘
```

**Key Measurements:**
- Avatar container: 70-80% viewport height (initial state)
- Input field: 80px height, 40px from bottom, 40px horizontal padding
- Sidebar: 72px collapsed, 240px expanded (desktop only)

**Responsive Breakpoints:**
- **Desktop (≥1024px)**: Persistent sidebar, horizontal layouts (side-by-side)
- **Tablet (768-1023px)**: Collapsible sidebar, horizontal layouts work
- **Mobile Portrait (<768px)**: Bottom nav, **vertical stacking** (avatar top, messages bottom)
- **Mobile Landscape**: Horizontal layouts work (sufficient width)

### Conversation Screen (Modal-Aware Layouts)

**Voice Mode (Oral Conversation):**
```
┌─────────────────────────────────────────────┐
│  [Sidebar]      [Avatar 70-80%]       [Side]│
│                                              │
│               ╭─────────────╮               │
│               │   Avatar    │               │
│               │ Center Stage│               │
│               │  Full Body  │               │
│               ╰─────────────╯               │
│                                              │
│          [Voice Indicator Pulsing]          │
│       [Optional Floating Captions]          │
│                                              │
│     [Minimized Chat UI - Slide Up Icon]     │
└─────────────────────────────────────────────┘
```
- **Avatar**: Center, 70-80% height, full presence
- **Chat UI**: Hidden/minimized (slide down)
- **Voice indicator**: Pulsing ring or waveform around avatar
- **Transcript**: Optional floating captions for accessibility
- **Toggle**: Small text bubble icon to enable chat

**Text Mode (Chat Conversation):**
```
┌─────────────────────────────────────────────┐
│  [Sidebar]  [Avatar 30%]  [Messages 70%]    │
│                                              │
│   ╭─────╮     ┌─────────────────────┐      │
│   │Avatar│     │ AI Message          │      │
│   │Left │     │ Glassmorphic card   │      │
│   │Stable│     └─────────────────────┘      │
│   ╰─────╯                                    │
│              ┌─────────────────────┐         │
│              │ User Message        │         │
│              └─────────────────────┘         │
│                                              │
│     [Input Field + Mic Icon Toggle]         │
└─────────────────────────────────────────────┘
```
- **Avatar**: Left 30%, stable throughout conversation
- **Messages**: Right 70%, full readability
- **Input**: Persistent bottom with voice toggle
- **Layout**: Stable, no shifting during conversation

**Hybrid Mode (Both Modalities Active):**
```
┌─────────────────────────────────────────────┐
│  [Sidebar]  [Avatar 40%]  [Messages 60%]    │
│                                              │
│     ╭─────╮   ┌─────────────────────┐      │
│     │Avatar│   │ AI Message          │      │
│     │Balanced  │ With transcript     │      │
│     ╰─────╯   └─────────────────────┘      │
│                                              │
│              ┌─────────────────────┐         │
│              │ User Message        │         │
│              └─────────────────────┘         │
│                                              │
│     [Input: Voice + Text Both Active]       │
└─────────────────────────────────────────────┘
```
- **Avatar**: Balanced 40%, visible but not dominant
- **Messages**: 60%, visible with transcripts
- **Input**: Both voice and text available
- **Use case**: User wants visual conversation history while speaking

**Thinking State (Any Mode):**
- Avatar: Slightly receded (scale 0.95)
- Glow: Increased intensity (pulsing)
- Messages: Dimmed slightly (0.8 opacity) in text/hybrid mode
- Voice indicator: Changes to "processing" animation in voice mode

### Mobile-Specific Layouts (Portrait <768px)

**Voice Mode (Mobile):**
```
┌─────────────────────┐
│   [Bottom Nav]      │
│                     │
│   ╭─────────────╮   │
│   │   Avatar    │   │
│   │  70% Height │   │
│   │ Center Stage│   │
│   ╰─────────────╯   │
│                     │
│ [Voice Indicator]   │
│ [Optional Captions] │
│                     │
│ [Minimized Chat]    │
└─────────────────────┘
```
- **Layout**: Same as desktop, works perfectly
- **Avatar**: 70% height, centered, full width
- **Chat**: Minimized, slide-up to activate

**Text Mode (Mobile):**
```
┌─────────────────────┐
│   [Bottom Nav]      │
│                     │
│ ╭─────────────────╮ │
│ │   Avatar 40%    │ │
│ │   Full Width    │ │
│ ╰─────────────────╯ │
│                     │
│ ┌─────────────────┐ │
│ │ AI Message      │ │
│ └─────────────────┘ │
│ ┌─────────────────┐ │
│ │ User Message    │ │
│ └─────────────────┘ │
│                     │
│ [Input Field]       │
└─────────────────────┘
```
- **Layout**: Vertical stacking (not side-by-side)
- **Avatar**: Top 40%, full width
- **Messages**: Bottom 60%, full width, scrollable
- **Rationale**: Side-by-side creates cramped columns on narrow screens

**Hybrid Mode (Mobile):**
```
┌─────────────────────┐
│   [Bottom Nav]      │
│                     │
│ ╭─────────────────╮ │
│ │   Avatar 30%    │ │
│ │   Full Width    │ │
│ ╰─────────────────╯ │
│                     │
│ ┌─────────────────┐ │
│ │ Messages 70%    │ │
│ │ With Transcript │ │
│ │   Scrollable    │ │
│ └─────────────────┘ │
│                     │
│ [Voice + Text Input]│
└─────────────────────┘
```
- **Layout**: Vertical stacking
- **Avatar**: Top 30%, full width
- **Messages**: Bottom 70%, full width
- **Both modalities**: Available but vertically arranged

**Mobile Landscape:**
- Uses desktop horizontal layouts (sufficient width for side-by-side)
- Avatar left, messages right works well in landscape orientation

**Mobile Layout Strategy:**
- **Voice mode**: ✅ Works identically to desktop (avatar-centric, no space constraints)
- **Text/Hybrid modes**: 📱 Vertical stacking instead of horizontal split
- **Rationale**: Portrait width (375-430px) too narrow for side-by-side layout
- **Benefit**: Avatar remains visible and prominent even in text mode
- **Transition**: Smooth 800ms animations between modes, stable during conversation

### Settings/Admin Screens

**Three-Pane Layout:**
```
┌──────────┬─────────────────────┬──────────┐
│ Sidebar  │   Main Content      │ Optional │
│ 240px    │   Fluid width       │  Panel   │
│          │                     │          │
│ Nav      │   Settings Cards    │ Context  │
│ Items    │   Form Fields       │ Help     │
│          │   Data Tables       │          │
└──────────┴─────────────────────┴──────────┘
```

**Avatar Presence:**
- **Minimal mode**: Small avatar (32px) in header
- **Ambient mode**: Subtle avatar presence in corner
- **Hidden mode**: Avatar off-screen, focus on content

## Avatar Integration Patterns

### Modal-Aware Avatar Presence

**Current State (Limited):**
- Avatar confined to circular viewport (~15% screen)
- Static positioning regardless of context
- Minimal environmental feedback
- No modality awareness

**Target State (Modal-Aware):**
- **Voice mode**: Avatar 70-80% height, center stage, chat minimized
- **Text mode**: Avatar 30% left, stable, chat prominent 70% right
- **Hybrid mode**: Avatar 40% balanced, chat 60% visible
- Full-body presence with depth-of-field background
- Environmental mood layers (gradients, particles)

**Implementation Approach:**
1. Expand WebView container to support 30-80% viewport height (modal-dependent)
2. Adjust Three.js camera for full-body framing
3. Add modal-aware positioning system (voice/text/hybrid)
4. Implement smooth 800ms transitions on modality switch
5. Add environmental mood gradient system
6. Create voice indicator animations (pulsing ring, waveform)

### Message Emanation Pattern

**Spatial Relationship:**
- User messages: Elevation 3, right-aligned
- Avatar: Elevation 5, center/left
- AI messages: Elevation 4, flow from avatar direction

**Visual Connection:**
- AI messages inherit 8% mood-colored glow from avatar
- Subtle particle trails from avatar to message (optional)
- Proximity-based glow intensity

### Environmental Mood Layers

**Background System:**
- **Base layer**: Radial gradient (current implementation)
- **Mood layer**: Color shifts based on emotion (warm amber, cool blue, soft purple)
- **Particle layer**: Floating light motes, ambient effects
- **Depth layer**: Blur increases during focus, decreases during casual

**Transition Timing:**
- Mood shifts: 1.2s smooth cubic-bezier
- Particle effects: 2-4s fade in/out
- Depth changes: 800ms synchronized with avatar movement

## Responsive Grid System

### Breakpoint Strategy

**Desktop (≥1024px):**
- 12-column grid, 1200px max width
- Persistent sidebar navigation
- Full avatar presence with side panels
- Horizontal space for rich layouts

**Tablet (768-1023px):**
- 8-column grid, 100% width
- Collapsible sidebar
- Full avatar, adaptive message layout
- Optimized for portrait/landscape

**Mobile (<768px):**
- 4-column grid, 100% width
- Bottom tab navigation
- Avatar 50-60% height
- Vertical-optimized layouts

### Adaptive Component Sizing

**Avatar:**
- **Desktop/Tablet (≥768px)**: 
  - Voice mode: 70-80% height, full body, centered
  - Text mode: 30% width left, full height
  - Hybrid mode: 40% width, full height
- **Mobile Portrait (<768px)**:
  - Voice mode: 70% height, full width, centered
  - Text mode: 40% height, full width, top
  - Hybrid mode: 30% height, full width, top

**Messages:**
- **Desktop**: Max 800px width, 40px horizontal padding, right 70%
- **Tablet**: Max 90% width, 24px padding, right 70%
- **Mobile Portrait**: Full width (95%), 16px padding, bottom 60-70%
- **Mobile Landscape**: Right 70% (desktop layout)

**Input Field:**
- **Desktop**: 800px max width, centered
- **Tablet**: 90% width, 24px padding
- **Mobile**: 95% width, 16px padding, persistent bottom

## Spatial Composition Rules

### Depth Staging (Z-Index Hierarchy)

**Layer 0 (Background):** Environmental gradients, mood colors
**Layer 1 (Drawers):** Sidebar, side panels (elevation 1)
**Layer 2 (Content):** Message cards, settings panels (elevation 2)
**Layer 3 (User Input):** User messages, input field (elevation 3)
**Layer 4 (AI Output):** AI messages, thinking cards (elevation 4)
**Layer 5 (Avatar):** Avatar presence, highest focus (elevation 5)
**Layer 6 (Overlays):** Modals, dialogs, notifications (elevation 6)

### Floating Element Spacing

**Minimum Clearances:**
- Screen edges: 16px mobile, 40px desktop
- Between elements: 16px minimum, 24px preferred
- Avatar to messages: 24px vertical gap
- Input to screen bottom: 40px desktop, 20px mobile

**Maximum Widths:**
- Content containers: 1200px
- Message bubbles: 800px
- Input fields: 800px
- Settings panels: 1000px

## Interaction Patterns

### Modal Transition Animations

**Modality Switch Transitions:**
- **Voice → Text**: Avatar slides left to 30% (800ms), chat slides up from bottom
- **Text → Voice**: Chat slides down, avatar centers and enlarges to 70-80% (800ms)
- **Any → Hybrid**: Avatar and chat smoothly adjust to 40/60 split (800ms)
- **Thinking state**: Avatar scales down (0.95), glow pulses (any mode)

**Key Principles:**
- Transitions only occur when **user switches modality**, not per message
- Layout remains **completely stable** during active conversation
- Smooth 800ms cubic-bezier transitions for all mode changes
- No distracting back-and-forth shifting

**Gesture Interactions:**
- **Swipe up on avatar**: Expand to full-screen focus mode
- **Tap avatar**: Quick attention ping (wave animation)
- **Long press**: Open avatar settings/mood selector
- **Pinch**: Zoom avatar in/out for preferred framing

### Message Flow Animations

**AI Message Appearance:**
1. Fade in from avatar direction (400ms)
2. Slide into position (300ms, ease-out)
3. Inherit proximity glow from avatar
4. Settle with subtle bounce (100ms)

**User Message Appearance:**
1. Optimistic immediate display
2. Slide up from input field (250ms)
3. Fade in with scale (0.95 → 1.0)
4. Settle at elevation 3

## Accessibility Considerations

### Reduced Motion Mode
- Disable avatar position transitions
- Remove particle effects
- Simplify mood gradient transitions
- Maintain spatial relationships without animation

### High Contrast Mode
- Increase border visibility (2px solid)
- Remove subtle gradients
- Boost text contrast to WCAG AAA
- Simplify glassmorphic effects

### Screen Reader Navigation
- Avatar described as "AICO avatar, [current state]"
- Messages announced with role and timestamp
- Spatial relationships conveyed through semantic HTML
- Focus order: Input → Messages → Avatar → Navigation

## Implementation Guidelines

### Component Composition Pattern

**Screen Structure:**
```dart
Scaffold(
  body: Stack([
    // Layer 0: Background
    EnvironmentalGradient(moodColor),
    
    // Layer 1-2: Sidebar/Content
    Row([
      AdaptiveSidebar(),
      Expanded(
        // Layer 5: Avatar
        AvatarContainer(height: 0.6),
        
        // Layer 2-4: Messages
        ConversationMessages(),
        
        // Layer 3: Input
        FloatingInput(),
      ),
    ]),
  ]),
)
```

### Avatar Container Sizing

**Current Implementation:**
- Fixed circular viewport in center
- ~15% screen coverage

**Target Implementation:**
- Flexible container: 60-70% viewport height
- Full-width WebView with transparent background
- Conversation-aware positioning (left/center/back)
- Smooth transitions between states

### State-Driven Layout

**Layout responds to:**
- `ConversationModality`: voice, text, hybrid (primary driver)
- `ConversationState`: idle, listening, thinking, speaking
- `UserActivity`: speaking, typing, scrolling, idle
- `SystemState`: connecting, processing, error

**Modality Enum:**
```dart
enum ConversationModality {
  voice,    // Avatar center 70-80%, chat minimized
  text,     // Avatar left 30%, chat prominent 70%
  hybrid,   // Avatar 40%, chat 60%, both active
}
```

## Performance Optimization

### Layout Efficiency
- Use `const` constructors for static layouts
- Minimize rebuilds with `Consumer` widgets
- Cache layout calculations
- Lazy-load off-screen content

### Animation Performance
- Hardware-accelerated transforms only
- Avoid layout-triggering animations
- Use `RepaintBoundary` for avatar container
- Limit simultaneous animations to 3-4

### Responsive Loading
- Load full avatar on desktop immediately
- Progressive enhancement on mobile
- Defer particle effects until idle
- Reduce quality on low-end devices

## Design Tokens

### Spacing Scale
- `xs`: 4px
- `sm`: 8px
- `md`: 16px
- `lg`: 24px
- `xl`: 40px
- `xxl`: 64px

### Border Radius Scale
- `small`: 12px (chips, tags)
- `medium`: 20px (cards, buttons)
- `large`: 28px (message bubbles)
- `xlarge`: 36px (main containers)

### Elevation Scale
- `0`: Background (no shadow)
- `1`: Drawers (subtle shadow)
- `2`: Content cards (medium shadow)
- `3`: User input (pronounced shadow)
- `4`: AI output (strong shadow)
- `5`: Avatar (maximum shadow)
- `6`: Overlays (dramatic shadow)

## Future Enhancements

### Spatial Audio Integration
- Avatar voice positioned in stereo field
- Environmental audio based on mood
- Haptic feedback synchronized with avatar

### AR/VR Adaptation
- Spatial positioning in 3D space
- Gaze-based interaction
- Environmental mapping
- Gesture recognition

### Multi-Avatar Scenarios
- Group conversations with multiple avatars
- Spatial positioning for speaker identification
- Individual mood indicators
- Coordinated animations

## Conclusion

AICO's UI layout system prioritizes avatar presence while adapting to user interaction preferences. By implementing **modal-aware layouts** that respond to voice vs. text modalities, we create an interface that feels natural regardless of how the user chooses to communicate.

**Key Design Principles:**
- **Voice mode**: Avatar takes center stage (70-80%), mimicking face-to-face conversation
- **Text mode**: Avatar remains present (30%) while chat gets functional space (70%)
- **Hybrid mode**: Balanced layout (40/60) for users who want both
- **Stable during conversation**: Layout changes only on modality switch, never per message
- **Smooth transitions**: 800ms transitions feel natural, not jarring

The key is **spatial relationships that adapt to interaction modality**: in voice mode, you're talking to a person; in text mode, you're messaging with a visible companion; in hybrid mode, you have both. Every layout decision serves the goal of making AICO feel genuinely present while respecting how the user wants to interact.
