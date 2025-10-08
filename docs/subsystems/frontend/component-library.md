# Component Library

## Overview

AICO's component library implements atomic design principles with emotional presence, accessibility, and cross-platform consistency. The library creates award-winning user experiences through minimalist design, zero-barrier interactions, and sophisticated theming supporting light/dark modes with fully configurable color systems.

### Design Excellence Standards

**Minimalism & Clarity**: Ample whitespace, crisp typography, and visual clarity create immediately understandable interfaces users can explore intuitively.

**Zero-Barrier Interactions**: Components prioritize immediate comprehension with visually prominent actions, consistent placement, and progressive disclosure revealing complexity only when needed.

**Emotional Presence**: Sophisticated emotional expression through subtle micro-interactions, breathing animations, and mood-responsive visual states create genuine connection.

**Accessibility Excellence**: WCAG AA+ compliance with comprehensive keyboard navigation, screen reader support, and color-independent interaction patterns ensure universal usability.

## Theming Architecture

### Dynamic Theme System

Sophisticated theming system eliminates hardcoded values and enables complete visual customization through semantic design tokens. All visual properties—colors, spacing, typography, animations—are tokenized for easy modification without touching component code.

**Light/Dark Mode Support**: Native system-preference detection with smooth transitions. Each theme token has light and dark variants that automatically adapt.

**Configurable Accent System**: Default soft purple (`#B8A1EA`) accent with full color system reconfiguration through theme files. Accent colors used strategically for emphasis, never as large background areas.

### Theme Configuration

```dart
class AicoTheme {
  final ColorScheme colors;
  final AccentColors accents;
  final TypographyScale typography;
  final SpacingScale spacing;
}

static final lightTheme = AicoTheme(
  colors: ColorScheme(
    background: AicoColors.neutralWhite,    // #F5F6FA
    surface: AicoColors.pureWhite,          // #FFFFFF
  ),
  accents: AccentColors(
    primary: AicoColors.softLavender,       // #B8A1EA
    success: AicoColors.mint,               // #8DD6B8
    warning: AicoColors.coral,              // #ED7867
  ),
);
```

## Design System Foundation

### Atomic Design Hierarchy

**Atoms**: Fundamental UI elements (buttons, inputs, icons)
**Molecules**: Simple combinations forming functional units (cards, message bubbles)
**Organisms**: Complex components combining multiple elements (conversation interface, settings panel)
**Templates**: Page-level organization patterns with consistent spacing
**Pages**: Complete interfaces with real content and state

## Core Components

### Atoms

Fundamental UI elements embodying minimalism, accessibility, and emotional presence through sophisticated theming and responsive behavior.

#### AicoButton
Primary interaction element with zero-barrier interaction principle and immediate visual affordance.

**Variants**: Primary, Secondary, Minimal, Destructive
**States**: Default, Hover, Pressed, Disabled, Loading
**Features**: WCAG AA+ contrast, keyboard navigation, micro-interactions with 200ms ease-out curves, responsive touch targets

```dart
class AicoButton extends StatelessWidget {
  Widget build(BuildContext context) {
    final theme = AicoTheme.of(context);
    return AnimatedContainer(
      decoration: BoxDecoration(
        color: _getBackgroundColor(theme),
        borderRadius: BorderRadius.circular(theme.spacing.radiusLarge),
      ),
      child: _buildContent(theme),
    );
  }
}
```

#### AicoTextField
Intuitive text input with emotional responsiveness and progressive disclosure through subtle visual cues.

**Variants**: Standard, Voice-enabled, Search, Multiline, Emotion-aware
**States**: Idle, Active, Error (coral accent), Success (mint accent), Disabled
**Features**: Keyboard navigation, screen reader compatibility, smooth focus transitions, voice input support

#### AicoAvatar
Central emotional presence with sophisticated mood expression through subtle animations and color shifts.

**Variants**: Main (96px), Mini (32px), Status (48px)
**States**: Idle, Thinking, Speaking, Listening, Attention
**Features**: Breathing effects, mood ring pulsing, expression transitions, semantic mood announcements

#### AicoIcon
Consistent iconography with theme-aware styling using custom AICO icon set with Material Icons fallback.

**Sizes**: Small (16px), Medium (24px), Large (32px), XLarge (48px)
**Features**: Semantic color roles, sufficient contrast ratios, accessibility labels

### Molecules

Functional units combining atoms with AICO's design principles of clarity, emotional presence, and zero-barrier interaction.

#### AicoCard
Content container with consistent elevation and spacing.

**Variants**: Default, Interactive, Elevated, Flat
**Features**: Responsive padding, theme-aware shadows, interaction states, semantic container roles

#### AicoMessageBubble
Conversation message display adapting visual treatment based on emotional context and sender through subtle color variations and animations.

**Variants**: User, Assistant, System, Emotion
**States**: Sending, Delivered, Read, Failed
**Features**: Gentle slide-in animations, typing indicators, emotional pulse effects, message role announcements

## System Transparency Components

### Progressive Disclosure Implementation

Components implement award-winning UX principles through progressive disclosure and system transparency.

#### ProgressIndicator
Clear visual feedback for long-running operations with meaningful status descriptions.

**Variants**: Linear, Circular, Stepped, Indeterminate
**Features**: Percentage display, contextual status text, smooth animations

#### SystemStatusBar
Subtle system health communication through color-coded indicators with contextual text.

**Features**: Collapsible design, non-alarming constraint communication, connection status

#### ActivityIndicator
Real-time system activity transparency showing current operations and queue status.

**States**: Idle, Processing, Waiting, Error
**Features**: Animated activity indicators, clear operation communication

## Implementation Guidelines

### Component Development Standards

Each component must support full theme customization, smooth light/dark transitions, comprehensive accessibility features, sophisticated micro-interactions, and atomic design hierarchy principles to maintain award-winning UX standards.

**Theme Integration Best Practices**:
- Never hardcode values—all visual properties reference theme tokens
- Use semantic color roles rather than specific color values
- Implement responsive scaling with theme-defined scales
- Ensure accessibility compliance across all theme variations

```dart
abstract class AicoWidget extends StatelessWidget {
  AicoTheme get theme => AicoTheme.of(context);
  String? get semanticLabel;
}
```

### Usage Principles

- **Consistency**: Use established components before creating new ones
- **Accessibility**: Every component meets WCAG AA+ standards
- **Performance**: Optimized for smooth animations and minimal rebuilds
- **Composition**: Build complex components from simpler atomic elements

This component library architecture ensures AICO's interface achieves design award recognition while maintaining complete theme flexibility and accessibility excellence through clean separation between theme tokens and component implementation.
