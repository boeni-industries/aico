import 'package:flutter/material.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/atom-one-dark.dart';
import 'package:flutter_highlight/themes/atom-one-light.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:markdown/markdown.dart' as md;

/// Markdown content renderer for AI responses
/// 
/// Provides rich text formatting with:
/// - Code syntax highlighting
/// - Proper heading hierarchy (NO underlines)
/// - Link styling
/// - List formatting
/// - Inline code styling
/// 
/// Follows AICO design system with glassmorphism aesthetics
/// Uses flutter_markdown for full styling control
class MarkdownContent extends StatelessWidget {
  final String data;
  final bool isDark;
  final Color? accentColor;

  const MarkdownContent({
    super.key,
    required this.data,
    required this.isDark,
    this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final effectiveAccentColor = accentColor ?? theme.colorScheme.primary;

    final normalizedData = normalizeMarkdownForRendering(data);

    return MarkdownBody(
      data: normalizedData,
      selectable: true,
      styleSheet: _buildStyleSheet(theme, effectiveAccentColor),
      builders: {
        'code': CodeElementBuilder(isDark: isDark),
      },
      extensionSet: md.ExtensionSet.gitHubFlavored,
    );
  }

  static String normalizeMarkdownForRendering(String input) {
    final text = input.replaceAll('\r\n', '\n').trim();
    if (text.isEmpty) return text;

    final lines = text.split('\n');

    int? minIndent;
    for (final line in lines) {
      if (line.trim().isEmpty) continue;
      final indent = _leadingSpaces(line);
      minIndent = minIndent == null ? indent : (indent < minIndent ? indent : minIndent);
    }

    if (minIndent == null || minIndent == 0) return text;

    return lines
        .map((line) {
          if (line.trim().isEmpty) return '';
          if (line.length <= minIndent!) return line.trimLeft();
          return line.substring(minIndent);
        })
        .join('\n')
        .trim();
  }

  static String stripMarkdownForPreview(String input, {int? maxChars}) {
    var text = normalizeMarkdownForRendering(input);
    if (text.isEmpty) return text;

    text = text
        // Links: [text](url) -> text
        .replaceAll(RegExp(r'\[([^\]]+)\]\(([^)]+)\)'), r'$1')
        // Inline code: `code` -> code
        .replaceAll(RegExp(r'`([^`]+)`'), r'$1')
        // Bold/italic: **x**/*x*/__x__/_x_ -> x
        .replaceAll(RegExp(r'(\*\*|__)(.*?)\1'), r'$2')
        .replaceAll(RegExp(r'(\*|_)(.*?)\1'), r'$2')
        // Headings and blockquotes
        .replaceAll(RegExp(r'^[ \t]*#{1,6}[ \t]+', multiLine: true), '')
        .replaceAll(RegExp(r'^[ \t]*>[ \t]?', multiLine: true), '')
        // Unordered/ordered list markers
        .replaceAll(RegExp(r'^[ \t]*([-*+]|\d+\.)[ \t]+', multiLine: true), '')
        // Horizontal rules
        .replaceAll(RegExp(r'^[ \t]*(-{3,}|\*{3,}|_{3,})[ \t]*$', multiLine: true), '')
        // Collapse whitespace
        .replaceAll(RegExp(r'\n{3,}'), '\n\n')
        .trim();

    if (maxChars != null && maxChars > 0 && text.length > maxChars) {
      return '${text.substring(0, maxChars)}...';
    }
    return text;
  }

  static int _leadingSpaces(String line) {
    var i = 0;
    while (i < line.length && line.codeUnitAt(i) == 32) {
      i++;
    }
    return i;
  }

  /// Build markdown style sheet matching AICO design system
  MarkdownStyleSheet _buildStyleSheet(ThemeData theme, Color accentColor) {
    final textColor = theme.colorScheme.onSurface;

    return MarkdownStyleSheet(
      // Paragraph styling
      p: theme.textTheme.bodyMedium?.copyWith(
        height: 1.6,
        letterSpacing: 0.2,
        color: textColor,
      ),
      
      // Heading styles - clean, no underlines
      h1: theme.textTheme.headlineMedium?.copyWith(
        fontWeight: FontWeight.bold,
        color: textColor,
        height: 1.3,
      ),
      h2: theme.textTheme.headlineSmall?.copyWith(
        fontWeight: FontWeight.bold,
        color: textColor,
        height: 1.3,
      ),
      h3: theme.textTheme.titleLarge?.copyWith(
        fontWeight: FontWeight.w600,
        color: textColor,
        height: 1.3,
      ),
      
      // Heading padding
      h1Padding: const EdgeInsets.only(top: 16, bottom: 8),
      h2Padding: const EdgeInsets.only(top: 16, bottom: 8),
      h3Padding: const EdgeInsets.only(top: 12, bottom: 6),
      
      // Code styling
      code: TextStyle(
        fontSize: 14,
        fontFamily: 'monospace',
        backgroundColor: isDark 
            ? Colors.white.withValues(alpha: 0.1)
            : Colors.grey.shade200,
        color: accentColor,
      ),
      
      // Code block styling
      codeblockDecoration: BoxDecoration(
        color: isDark 
            ? Colors.black.withValues(alpha: 0.3)
            : Colors.grey.shade100,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isDark 
              ? Colors.white.withValues(alpha: 0.1)
              : Colors.grey.shade300,
          width: 1,
        ),
      ),
      codeblockPadding: const EdgeInsets.all(16),
      
      // Link styling
      a: TextStyle(
        color: accentColor,
        decoration: TextDecoration.underline,
        decorationColor: accentColor.withValues(alpha: 0.5),
      ),
      
      // List styling
      listBullet: TextStyle(
        color: accentColor,
        fontSize: 16,
      ),
      
      // Blockquote styling
      blockquote: TextStyle(
        color: textColor.withValues(alpha: 0.8),
        fontStyle: FontStyle.italic,
      ),
      blockquoteDecoration: BoxDecoration(
        border: Border(
          left: BorderSide(
            color: accentColor,
            width: 4,
          ),
        ),
      ),
      blockquotePadding: const EdgeInsets.only(left: 16, top: 8, bottom: 8),
      
      // Horizontal rule
      horizontalRuleDecoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: isDark 
                ? Colors.white.withValues(alpha: 0.15)
                : Colors.grey.withValues(alpha: 0.3),
            width: 1,
          ),
        ),
      ),
      
      // Emphasis
      em: const TextStyle(fontStyle: FontStyle.italic),
      strong: const TextStyle(fontWeight: FontWeight.bold),
    );
  }
}

/// Custom code block builder with syntax highlighting
class CodeElementBuilder extends MarkdownElementBuilder {
  final bool isDark;

  CodeElementBuilder({required this.isDark});

  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final language = element.attributes['class']?.replaceFirst('language-', '') ?? '';
    final code = element.textContent;

    return HighlightView(
      code,
      language: language.isEmpty ? 'plaintext' : language,
      theme: isDark ? atomOneDarkTheme : atomOneLightTheme,
      padding: const EdgeInsets.all(16),
      textStyle: const TextStyle(
        fontSize: 14,
        fontFamily: 'monospace',
        height: 1.4,
      ),
    );
  }
}
