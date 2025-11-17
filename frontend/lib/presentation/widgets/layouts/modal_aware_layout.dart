import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/responsive/breakpoints.dart';
import '../../providers/layout_provider.dart';

/// Modal-aware layout that adapts to conversation modality and platform
/// 
/// Handles three conversation modes:
/// - Voice: Avatar center stage, chat minimized
/// - Text: Avatar left/top, chat prominent
/// - Hybrid: Balanced layout with both visible
/// 
/// Automatically switches between horizontal (desktop/tablet/landscape)
/// and vertical (mobile portrait) layouts based on screen size.
class ModalAwareLayout extends ConsumerWidget {
  final Widget avatar;
  final Widget messages;
  final Widget input;
  final Widget? sidebar;
  final VoidCallback? onShowChat;

  const ModalAwareLayout({
    super.key,
    required this.avatar,
    required this.messages,
    required this.input,
    this.sidebar,
    this.onShowChat,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final layoutState = ref.watch(layoutProvider);
    final isVertical = context.shouldUseVerticalLayout;

    return isVertical
        ? _VerticalLayout(
            avatar: avatar,
            messages: messages,
            input: input,
            layoutState: layoutState,
            onShowChat: onShowChat,
          )
        : _HorizontalLayout(
            avatar: avatar,
            messages: messages,
            input: input,
            sidebar: sidebar,
            layoutState: layoutState,
            onShowChat: onShowChat,
          );
  }
}

/// Horizontal layout for desktop, tablet, and mobile landscape
/// Avatar and messages side-by-side
class _HorizontalLayout extends StatelessWidget {
  final Widget avatar;
  final Widget messages;
  final Widget input;
  final Widget? sidebar;
  final LayoutState layoutState;
  final VoidCallback? onShowChat;

  const _HorizontalLayout({
    required this.avatar,
    required this.messages,
    required this.input,
    this.sidebar,
    required this.layoutState,
    this.onShowChat,
  });

  @override
  Widget build(BuildContext context) {
    final avatarWidthPercent = layoutState.getAvatarWidthPercent(false);
    final isChatVisible = layoutState.isChatVisible;
    final hasMessages = layoutState.hasMessages;

    return Stack(
      children: [
        // In text mode, use overlapping layout for more chat space
        if (isChatVisible)
          Row(
            children: [
              // Sidebar (desktop only)
              if (sidebar != null && context.isDesktop) sidebar!,

              // Avatar container - 45% of remaining space
              Expanded(
                flex: 45,
                child: avatar,
              ),

              // Messages and input container - 65% overlaps avatar by 10%
              Expanded(
                flex: 65,
                child: Column(
                  children: [
                    // Messages area
                    Expanded(child: messages),
                    
                    // Input field
                    Padding(
                      padding: EdgeInsets.all(context.horizontalPadding),
                      child: input,
                    ),
                  ],
                ),
              ),
            ],
          )
        else
          // Voice mode - avatar takes full width
          Row(
            children: [
              // Sidebar (desktop only)
              if (sidebar != null && context.isDesktop) sidebar!,

              // Avatar container - full width in voice mode
              Expanded(
                flex: (avatarWidthPercent * 100).round(),
                child: avatar,
              ),
            ],
          ),
        
        // Voice mode or initial state: input at bottom center (floats on top of avatar)
        if (!isChatVisible)
          Positioned(
            left: 40,
            right: 40,
            bottom: 20,
            child: input,
          ),

        // Voice mode with messages: show minimized chat indicator
        // Initial state: don't show indicator (user sees "I'm here" message)
        if (!isChatVisible && hasMessages)
          Positioned(
            bottom: 140, // Above input field (input is ~80px + 20px margin)
            right: 40,
            child: _MinimizedChatIndicator(onTap: onShowChat),
          ),
      ],
    );
  }
}

/// Vertical layout for mobile portrait
/// Avatar and messages stacked vertically
class _VerticalLayout extends StatelessWidget {
  final Widget avatar;
  final Widget messages;
  final Widget input;
  final LayoutState layoutState;
  final VoidCallback? onShowChat;

  const _VerticalLayout({
    required this.avatar,
    required this.messages,
    required this.input,
    required this.layoutState,
    this.onShowChat,
  });

  @override
  Widget build(BuildContext context) {
    final avatarHeightPercent = layoutState.getAvatarHeightPercent(true);
    final isChatVisible = layoutState.isChatVisible;
    final hasMessages = layoutState.hasMessages;

    return Column(
      children: [
        // Avatar container (top)
        SizedBox(
          height: MediaQuery.of(context).size.height * avatarHeightPercent,
          child: avatar,
        ),

        // Messages (bottom) - only in text/hybrid mode
        if (isChatVisible)
          Expanded(child: messages),

        // Voice mode with messages: minimized chat indicator
        // Initial state: empty space (user sees "I'm here" in avatar area)
        if (!isChatVisible && hasMessages)
          Expanded(
            child: Center(
              child: _MinimizedChatIndicator(onTap: onShowChat),
            ),
          ),
        
        // Initial state: spacer
        if (!isChatVisible && !hasMessages)
          const Expanded(child: SizedBox.shrink()),
        
        // Input field (always visible)
        Padding(
          padding: EdgeInsets.symmetric(
            horizontal: context.horizontalPadding,
            vertical: 16,
          ),
          child: input,
        ),
      ],
    );
  }
}

/// Minimized chat indicator for voice mode
/// Shows a glassmorphic button to expand chat UI
class _MinimizedChatIndicator extends StatefulWidget {
  final VoidCallback? onTap;
  
  const _MinimizedChatIndicator({this.onTap});

  @override
  State<_MinimizedChatIndicator> createState() => _MinimizedChatIndicatorState();
}

class _MinimizedChatIndicatorState extends State<_MinimizedChatIndicator> {
  bool _isHovered = false;
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final accentColor = const Color(0xFFB8A1EA);

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        onTapDown: (_) => setState(() => _isPressed = true),
        onTapUp: (_) => setState(() => _isPressed = false),
        onTapCancel: () => setState(() => _isPressed = false),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          decoration: BoxDecoration(
            // Glassmorphic background
            color: isDark
                ? Colors.white.withValues(alpha: _isPressed ? 0.12 : _isHovered ? 0.10 : 0.06)
                : Colors.white.withValues(alpha: _isPressed ? 0.85 : _isHovered ? 0.75 : 0.65),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(
              color: isDark
                  ? Colors.white.withValues(alpha: _isHovered ? 0.20 : 0.12)
                  : Colors.white.withValues(alpha: _isHovered ? 0.50 : 0.35),
              width: 1.5,
            ),
            boxShadow: [
              // Main floating shadow
              BoxShadow(
                color: Colors.black.withValues(alpha: isDark ? 0.5 : 0.12),
                blurRadius: _isHovered ? 32 : 24,
                offset: Offset(0, _isPressed ? 8 : 12),
                spreadRadius: -6,
              ),
              // Accent glow on hover
              if (_isHovered)
                BoxShadow(
                  color: accentColor.withValues(alpha: 0.25),
                  blurRadius: 40,
                  spreadRadius: -8,
                ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.chat_bubble_outline_rounded,
                size: 20,
                color: _isHovered
                    ? accentColor
                    : (isDark
                        ? Colors.white.withValues(alpha: 0.75)
                        : Colors.black.withValues(alpha: 0.70)),
              ),
              const SizedBox(width: 10),
              Text(
                'Show chat',
                style: TextStyle(
                  color: _isHovered
                      ? accentColor
                      : (isDark
                          ? Colors.white.withValues(alpha: 0.75)
                          : Colors.black.withValues(alpha: 0.70)),
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  letterSpacing: 0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
