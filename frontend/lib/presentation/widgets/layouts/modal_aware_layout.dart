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

  const ModalAwareLayout({
    super.key,
    required this.avatar,
    required this.messages,
    required this.input,
    this.sidebar,
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
          )
        : _HorizontalLayout(
            avatar: avatar,
            messages: messages,
            input: input,
            sidebar: sidebar,
            layoutState: layoutState,
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

  const _HorizontalLayout({
    required this.avatar,
    required this.messages,
    required this.input,
    this.sidebar,
    required this.layoutState,
  });

  @override
  Widget build(BuildContext context) {
    final avatarWidthPercent = layoutState.getAvatarWidthPercent(false);
    final messageWidthPercent = layoutState.getMessageWidthPercent(false);
    final isChatVisible = layoutState.isChatVisible;

    return Row(
      children: [
        // Sidebar (desktop only)
        if (sidebar != null && context.isDesktop) sidebar!,

        // Avatar container
        Expanded(
          flex: (avatarWidthPercent * 100).round(),
          child: avatar,
        ),

        // Messages container (hidden in voice mode)
        if (isChatVisible)
          Expanded(
            flex: (messageWidthPercent * 100).round(),
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

        // Voice mode: minimized chat indicator
        if (!isChatVisible)
          Positioned(
            bottom: 20,
            right: 20,
            child: _MinimizedChatIndicator(),
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

  const _VerticalLayout({
    required this.avatar,
    required this.messages,
    required this.input,
    required this.layoutState,
  });

  @override
  Widget build(BuildContext context) {
    final avatarHeightPercent = layoutState.getAvatarHeightPercent(true);
    final isChatVisible = layoutState.isChatVisible;

    return Column(
      children: [
        // Avatar container (top)
        SizedBox(
          height: MediaQuery.of(context).size.height * avatarHeightPercent,
          child: avatar,
        ),

        // Messages and input (bottom)
        if (isChatVisible)
          Expanded(
            child: Column(
              children: [
                // Messages area
                Expanded(child: messages),
                
                // Input field
                Padding(
                  padding: EdgeInsets.symmetric(
                    horizontal: context.horizontalPadding,
                    vertical: 16,
                  ),
                  child: input,
                ),
              ],
            ),
          ),

        // Voice mode: minimized chat indicator
        if (!isChatVisible)
          Padding(
            padding: const EdgeInsets.all(20),
            child: _MinimizedChatIndicator(),
          ),
      ],
    );
  }
}

/// Minimized chat indicator for voice mode
/// Shows a small button to slide up chat UI
class _MinimizedChatIndicator extends StatelessWidget {
  const _MinimizedChatIndicator();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface.withOpacity(0.12),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.chat_bubble_outline,
            size: 18,
            color: Colors.white.withOpacity(0.7),
          ),
          const SizedBox(width: 8),
          Text(
            'Show chat',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
