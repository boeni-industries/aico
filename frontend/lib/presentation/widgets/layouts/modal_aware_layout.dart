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
    final isChatVisible = layoutState.isChatVisible;

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

        // Voice mode: Chat is accessible via keyboard button in input area
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

        // Voice mode: Chat is accessible via keyboard button in input area
        
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
