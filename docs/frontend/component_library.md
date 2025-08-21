---
title: Component Library
---

# Component Library

## Overview

AICO's component library implements atomic design principles with a focus on emotional presence, accessibility, and cross-platform consistency. Components are built using the soft purple accent system and support dynamic theming, responsive layouts, and comprehensive accessibility features.

## Design System Foundation

### Atomic Design Hierarchy

#### Atoms (Basic Elements)
Fundamental UI elements that cannot be broken down further while maintaining their function.

#### Molecules (Component Groups)
Simple combinations of atoms that form functional units.

#### Organisms (Complex Components)
Sophisticated components combining molecules and atoms into distinct interface sections.

#### Templates (Layout Structures)
Page-level organization patterns that define consistent spacing and arrangement.

#### Pages (Complete Screens)
Fully realized interfaces that populate templates with real content and state.

## Component Categories

### 1. Atoms

#### AicoButton
**Purpose**: Primary interaction element with consistent styling and behavior
**Variants**: Primary, Secondary, Minimal, Destructive

**Design Specifications**:
- **Primary**: Soft purple background (#B8A1EA), white text, rounded corners (16px)
- **Secondary**: White background, soft purple border and text
- **Minimal**: Transparent background, soft purple text, no border
- **Destructive**: Coral background (#ED7867), white text

**States**: Default, Hover, Pressed, Disabled, Loading
**Accessibility**: WCAG AA contrast, keyboard focus, screen reader support
**Animation**: Subtle scale and color transitions (200ms ease-out)

#### AicoTextField
**Purpose**: Text input with consistent styling and validation
**Variants**: Standard, Voice-enabled, Search, Multiline

**Design Specifications**:
- **Border**: Subtle gray border with soft purple focus ring
- **Padding**: 16px horizontal, 12px vertical
- **Typography**: Inter 1.0rem, weight 400
- **States**: Default, Focus, Error, Disabled

**Features**:
- Voice input integration for voice-enabled variant
- Real-time validation with gentle error indication
- Placeholder text with appropriate contrast
- Character count for limited inputs

#### AicoIcon
**Purpose**: Consistent iconography across the application
**Library**: Custom AICO icon set with Material Icons fallback

**Specifications**:
- **Sizes**: 16px, 24px, 32px, 48px
- **Colors**: Inherit from parent or explicit color props
- **Accessibility**: Semantic labels and descriptions
- **Animation**: Subtle hover and interaction effects

#### AicoAvatar
**Purpose**: User and AICO representation with emotional expression
**Variants**: AICO (animated), User (static), Family Member

**Design Specifications**:
- **Sizes**: Mini (32px), Standard (64px), Large (96px), Hero (128px)
- **Shape**: Circular with subtle shadow
- **Animation**: Breathing effect, expression changes, attention indicators
- **Mood Ring**: Soft purple accent ring for emotional state indication

### 2. Molecules

#### MessageBubble
**Purpose**: Individual message display in conversation interface
**Variants**: User message, AICO message, System message

**Design Specifications**:
- **User Messages**: Right-aligned, soft purple background, white text
- **AICO Messages**: Left-aligned, white background, dark text
- **System Messages**: Center-aligned, minimal styling
- **Spacing**: 8px vertical between messages, 16px horizontal padding
- **Typography**: Inter 1.0rem for content, 0.875rem for metadata

**Features**:
- Timestamp display with relative time formatting
- Message status indicators (sending, sent, delivered, read)
- Reaction support with emoji picker integration
- Long-press context menu for message actions

#### ChatInput
**Purpose**: Message composition with voice and text input
**Components**: Text field, voice button, send button, attachment options

**Design Specifications**:
- **Container**: White background, subtle elevation, rounded corners
- **Layout**: Flexible text area with fixed action buttons
- **Voice Button**: Prominent positioning with recording state animation
- **Send Button**: Disabled state when no content, smooth enable transition

**Features**:
- Auto-expanding text area with maximum height
- Voice recording with visual feedback
- Typing indicators sent to backend
- Draft message persistence across sessions

#### StatusIndicator
**Purpose**: Connection and system status communication
**Variants**: Connected, Connecting, Offline, Error

**Design Specifications**:
- **Connected**: Green dot with "Connected" label
- **Connecting**: Animated pulsing orange dot with "Connecting..." label
- **Offline**: Gray dot with "Offline" label
- **Error**: Red dot with error description

**Animation**: Smooth color transitions, pulsing for active states
**Accessibility**: Color-blind friendly with text labels and icons

#### SettingsCard
**Purpose**: Configuration option presentation in settings screens
**Components**: Title, description, control element, optional icon

**Design Specifications**:
- **Container**: White background, rounded corners, subtle shadow
- **Layout**: Consistent padding (24px), clear visual hierarchy
- **Typography**: Inter medium weight for titles, regular for descriptions
- **Controls**: Switches, dropdowns, buttons integrated seamlessly

### 3. Organisms

#### ChatInterface
**Purpose**: Complete conversation experience with message history and input
**Components**: Message list, chat input, typing indicators, connection status

**Layout Structure**:
- **Header**: Connection status and conversation context
- **Message Area**: Scrollable message history with infinite scroll
- **Input Area**: Fixed bottom position with chat input molecule
- **Overlay Elements**: Typing indicators, connection alerts

**Features**:
- Smooth scrolling with message grouping by time
- Auto-scroll to bottom for new messages
- Pull-to-refresh for message history loading
- Keyboard avoidance for mobile platforms

#### AvatarDisplay
**Purpose**: Central avatar presentation with emotional expression and interaction
**Components**: Avatar, mood ring, expression overlay, interaction indicators

**Design Specifications**:
- **Container**: Centered positioning with breathing space
- **Avatar**: Large size (96px+) with smooth animation support
- **Mood Ring**: Animated ring around avatar showing emotional state
- **Expression Overlay**: Subtle visual effects for emotions and states

**Interaction States**:
- **Idle**: Gentle breathing animation
- **Listening**: Pulsing attention indicator
- **Thinking**: Contemplative animation pattern
- **Speaking**: Mouth movement synchronization
- **Emotional**: Expression-specific animations

#### SettingsPanel
**Purpose**: Comprehensive settings management with categorized options
**Components**: Category navigation, settings cards, action buttons

**Layout Structure**:
- **Navigation**: Left sidebar with setting categories
- **Content Area**: Scrollable settings cards for selected category
- **Actions**: Save, reset, and cancel buttons with clear hierarchy

**Categories**:
- **Appearance**: Theme, language, display preferences
- **Privacy**: Data controls, relationship settings, consent management
- **Voice**: Speech recognition, voice synthesis, language settings
- **Accessibility**: Screen reader, high contrast, motion preferences

#### UpdateDialog
**Purpose**: System update notification and management interface
**Components**: Update information, changelog, action buttons, progress indicator

**Design Specifications**:
- **Modal Overlay**: Semi-transparent background with centered dialog
- **Content**: Clear update description with version information
- **Changelog**: Expandable list of changes and improvements
- **Actions**: Install now, schedule, remind later options
- **Progress**: Visual progress bar during download and installation

### 4. Templates

#### MainLayout
**Purpose**: Primary application layout structure
**Components**: Navigation, content area, overlay management

**Responsive Behavior**:
- **Mobile**: Bottom tab navigation, full-screen content
- **Desktop**: Side navigation, multi-column content support
- **Web**: Browser-friendly layout with proper semantic structure

#### ChatLayout
**Purpose**: Conversation-focused layout optimization
**Components**: Minimal navigation, maximized chat area, contextual actions

**Features**:
- **Distraction-free**: Minimal UI chrome for focused conversation
- **Context-aware**: Navigation adapts to conversation state
- **Accessibility**: Proper heading structure and landmark regions

#### SettingsLayout
**Purpose**: Configuration interface with clear organization
**Components**: Category navigation, content panels, persistent actions

**Organization**:
- **Hierarchical**: Clear information architecture with breadcrumbs
- **Searchable**: Quick access to specific settings
- **Responsive**: Adaptive layout for different screen sizes

## Component Implementation

### Base Component Structure
```dart
// Base widget with consistent theming and accessibility
abstract class AicoWidget extends StatelessWidget {
  const AicoWidget({Key? key}) : super(key: key);
  
  // Consistent theme access
  AicoTheme get theme => AicoTheme.of(context);
  
  // Accessibility helpers
  String? get semanticLabel;
  String? get semanticHint;
}
```

### Theming Integration
```dart
// Theme-aware component implementation
class AicoButton extends AicoWidget {
  final String text;
  final VoidCallback? onPressed;
  final AicoButtonVariant variant;
  
  @override
  Widget build(BuildContext context) {
    final buttonTheme = theme.buttonTheme(variant);
    
    return Material(
      color: buttonTheme.backgroundColor,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          child: Text(
            text,
            style: buttonTheme.textStyle,
          ),
        ),
      ),
    );
  }
}
```

### Accessibility Implementation
```dart
// Comprehensive accessibility support
class AccessibleAicoButton extends AicoButton {
  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: semanticLabel ?? text,
      hint: semanticHint,
      button: true,
      enabled: onPressed != null,
      child: super.build(context),
    );
  }
}
```

## Component Guidelines

### Usage Principles
- **Consistency**: Use established components before creating new ones
- **Accessibility**: Every component must meet WCAG AA standards
- **Performance**: Optimize for smooth animations and minimal rebuilds
- **Theming**: Support both light and dark themes with dynamic switching

### Customization Guidelines
- **Props over variants**: Prefer configurable props to multiple variants
- **Composition**: Build complex components from simpler ones
- **State management**: Integrate with BLoC pattern for stateful components
- **Testing**: Include comprehensive widget tests for all components

### Documentation Requirements
- **API documentation**: Clear prop descriptions and usage examples
- **Visual examples**: Screenshots showing all variants and states
- **Accessibility notes**: Specific accessibility features and considerations
- **Usage guidelines**: When and how to use each component appropriately

This component library ensures consistent, accessible, and emotionally engaging user interfaces across all AICO platforms while supporting the design principles of progressive disclosure and offline-first functionality.
