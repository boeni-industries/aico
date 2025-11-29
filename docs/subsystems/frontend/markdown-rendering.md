# Markdown Rendering in AICO Frontend

## Overview

AICO uses `markdown_widget` with `flutter_highlight` to render rich markdown content in AI responses, providing a superior UX for formatted text, code snippets, and structured content.

## Architecture

### Components

1. **MarkdownContent Widget** (`lib/presentation/widgets/chat/markdown_content.dart`)
   - Presentation layer component
   - Encapsulates markdown rendering logic
   - Provides consistent styling across the app
   - Follows AICO glassmorphism design system

2. **MessageBubble Integration** (`lib/presentation/widgets/chat/message_bubble.dart`)
   - AI messages: Rendered with markdown support
   - User messages: Plain text (no markdown parsing needed)

### Design Decisions

**Why markdown_widget?**
- ✅ Full theme customization (dark/light mode)
- ✅ Built-in code syntax highlighting
- ✅ Selectable text for copy/paste
- ✅ Active maintenance and Flutter 3.x support
- ✅ Designed for chat/AI interfaces

**Rendering Strategy:**
- AI messages: Full markdown rendering with syntax highlighting
- User messages: Plain text (performance optimization)
- Code blocks: Syntax highlighting with VS Code themes
- Links: Styled with accent color, tap handling prepared

## Features

### Supported Markdown Elements

- **Headings** (H1-H3): Styled with theme typography
- **Paragraphs**: Proper line height and spacing
- **Code Blocks**: Syntax highlighting with `atom-one-dark` (dark mode) / `atom-one-light` (light mode)
- **Inline Code**: Accent-colored with background
- **Links**: Underlined with accent color (tap handling TODO)
- **Lists**: Bullet and numbered lists
- **Emphasis**: Bold, italic, strikethrough

### Styling

All markdown elements follow AICO's glassmorphism design:
- Consistent with message bubble aesthetics
- Dark/light mode support
- Accent color integration
- Proper spacing and typography hierarchy

## Usage

```dart
// In message bubble
if (widget.isFromAico)
  MarkdownContent(
    data: messageContent,
    isDark: isDark,
    accentColor: accentColor,
  )
```

## Future Enhancements

1. **URL Launching**: Implement secure URL opening with user confirmation
2. **LaTeX Support**: Add math equation rendering if needed
3. **Table Rendering**: Enhanced table styling
4. **Custom Tags**: Support for AICO-specific markdown extensions
5. **Copy Code Button**: Add copy button to code blocks

## Performance Considerations

- Markdown parsing is done on-demand during render
- Selectable text is enabled for accessibility
- Code highlighting uses efficient theme caching
- Widget rebuilds are minimized through proper state management

## Security

- Link tapping requires explicit user action
- No automatic URL opening (prevents phishing)
- Content is sanitized by markdown parser
- No script execution or HTML injection

## Dependencies

```yaml
markdown_widget: ^2.3.2+8  # Core markdown rendering
flutter_highlight: ^0.7.0   # Code syntax highlighting
```

## References

- [markdown_widget Documentation](https://pub.dev/packages/markdown_widget)
- [flutter_highlight Themes](https://pub.dev/packages/flutter_highlight)
- [AICO Design System](../design/glassmorphism.md)
